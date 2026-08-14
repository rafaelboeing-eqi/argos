#!/usr/bin/env python3
"""One-shot setup for the Argos Mercado module against the real PostgreSQL.

Run from inside backend/, with backend/.env pointing at the real database:

    cd backend
    python run_argos_market_setup.py

What it does, in order: validates database/schema/table preconditions
(read-only - aborts without changing anything if they don't match), applies
pending Alembic migrations (schema changes are scoped to argos_market_history
/ argos_metrics only - see backend/alembic/versions/), backfills ~180 days of
history for any futures asset or macro series that has no data yet, runs the
incremental daily collector, recomputes argos_metrics, then prints a
validation report. Safe to run more than once: assets/series that already
have data skip the full backfill, migrations that already ran are no-ops to
Alembic, and every write goes through the same dedup-safe upsert used
everywhere else in Argos - re-running never duplicates rows, it only fills in
whatever is still missing.

docs/argos_market_migration.sql documents the same schema changes in plain
SQL, for anyone who prefers to review/run them by hand in DBeaver - keep it
in sync if the Alembic migrations change.

Never touches anything outside argos_market_history/argos_metrics, never
drops a table, and never prints BRAPI_API_TOKEN or database credentials.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.repositories.market_repository import get_latest_reference_date, has_history_for_symbol
from app.services.market_data.config import (
    CATEGORY_FUTURES_CURVE,
    CATEGORY_MACRO,
    CATEGORY_TREASURY,
    FUTURES_ASSETS,
    MACRO_SERIES,
    TREASURY_ASSETS,
    TREASURY_HISTORY_BATCH_SIZE,
    TREASURY_LABELS,
)
from app.services.market_data.market_collector import MarketCollectorService, chunked
from app.services.market_data.market_metrics import MarketMetricsService

EXPECTED_DATABASE = "features"
EXPECTED_SCHEMA = "public"
REQUIRED_TABLES = ("argos_market_history", "argos_metrics")

BACKFILL_DAYS = 180

BACKEND_DIR = Path(__file__).resolve().parent


def abort(message: str) -> None:
    print(f"\nABORTADO: {message}", file=sys.stderr)
    sys.exit(1)


def validate_connection_scope() -> None:
    """Read-only checks against the real database. Never alters anything.

    Confirms we're talking to the right database/schema and that the only
    tables in play are argos_market_history/argos_metrics, per the project's
    database safety policy (see CLAUDE.md).
    """
    settings = get_settings()
    if engine is None:
        abort("DATABASE_* não configurado em backend/.env.")
    if not settings.brapi_configured:
        abort("BRAPI_API_TOKEN não configurado em backend/.env.")

    print("1) Validando conexão, banco e schema...")
    with engine.connect() as conn:
        current_db, current_schema = conn.execute(text("SELECT current_database(), current_schema()")).one()
        if current_db != EXPECTED_DATABASE:
            abort(f"Banco conectado é '{current_db}', esperado '{EXPECTED_DATABASE}'.")
        if current_schema != EXPECTED_SCHEMA:
            abort(f"Schema atual é '{current_schema}', esperado '{EXPECTED_SCHEMA}'.")
        print(f"   database={current_db} schema={current_schema} OK")

        existing_tables = set(
            conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name IN ('argos_market_history', 'argos_metrics')"
                ),
                {"schema": EXPECTED_SCHEMA},
            ).scalars()
        )
        missing_tables = set(REQUIRED_TABLES) - existing_tables
        if missing_tables:
            abort(
                f"Tabela(s) ausente(s) em {EXPECTED_SCHEMA}: {sorted(missing_tables)}. "
                "Este script só cria/altera argos_market_history e argos_metrics - "
                "elas precisam existir (mesmo que só com a coluna id)."
            )
        print(f"   tabelas encontradas: {sorted(existing_tables)}")

    print("Escopo OK - nada foi alterado ainda.\n")


def apply_migrations() -> None:
    """Runs `alembic upgrade head`. Alembic's env.py only ever maps
    argos_market_history/argos_metrics (see app/models/base.py), so this can
    never touch any other table."""
    print("2) Aplicando migrations (alembic upgrade head)...")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    print("   Migrations em dia.\n")


def backfill_futures_if_needed(db, collector: MarketCollectorService, asset: str, start: date, end: date) -> str:
    if get_latest_reference_date(db, CATEGORY_FUTURES_CURVE, asset) is not None:
        return f"{asset}: já possui histórico, backfill completo pulado"

    symbols = collector.discover_curve_symbols(asset)
    if not symbols:
        return f"{asset}: nenhum contrato encontrado na curva atual (brapi indisponível ou ativo sem dados agora)"

    totals = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    failed = []
    for symbol in symbols:
        result = collector.collect_futures_history(asset, symbol, start_date=start, end_date=end)
        if "error" in result:
            failed.append(symbol)
            continue
        for key in totals:
            totals[key] += result.get(key, 0)

    summary = f"{asset}: backfill de {len(symbols)} contrato(s) -> {totals}"
    if failed:
        summary += f" | falharam: {failed}"
    return summary


def backfill_macro_if_needed(db, collector: MarketCollectorService, slug: str, start: date, end: date) -> str:
    if get_latest_reference_date(db, CATEGORY_MACRO, slug) is not None:
        return f"{slug}: já possui histórico, backfill completo pulado"

    result = collector.collect_macro_history(symbols=[slug], start_date=start, end_date=end)
    if "error" in result:
        return f"{slug}: falhou no backfill ({result['error']})"
    return f"{slug}: backfill -> created={result['created']} updated={result['updated']} unchanged={result['unchanged']}"


def backfill_treasury_if_needed(db, collector: MarketCollectorService, asset: str, start: date, end: date) -> str:
    """Unlike futures/macro, this checks per-BOND history (not just per-asset):
    Tesouro Direto gets new issuances fairly often, so a bond added after the
    first backfill still needs its own history even though the asset overall
    already has data.

    Prints [i/N] progress per bond as it goes - this step used to run silent for
    minutes, which looked like it had hung.
    """
    label = TREASURY_LABELS.get(asset, asset)
    bonds = collector.discover_treasury_bonds(asset)
    if not bonds:
        return f"{asset}: nenhum título encontrado agora (brapi indisponível ou filtro sem resultado)"

    new_symbols = [bond["symbol"] for bond in bonds if not has_history_for_symbol(db, CATEGORY_TREASURY, bond["symbol"])]
    if not new_symbols:
        return f"{asset}: já possui histórico para todos os {len(bonds)} títulos atuais, backfill pulado"

    total = len(new_symbols)
    print(f"   {label}: descobertos {total} título(s) novo(s) de {len(bonds)}")

    totals = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    failed_batches = []
    done = 0

    def report_done(symbol: str, counts: dict) -> None:
        nonlocal done
        done += 1
        print(f"   [{done}/{total}] {symbol} concluído - created={counts['created']} unchanged={counts['unchanged']}")

    for batch in chunked(new_symbols, TREASURY_HISTORY_BATCH_SIZE):
        for offset, symbol in enumerate(batch):
            print(f"   [{done + offset + 1}/{total}] {symbol} processando")
        result = collector.collect_treasury_history(
            asset, batch, start_date=start, end_date=end, progress_callback=report_done
        )
        if "error" in result:
            failed_batches.append(batch)
            done += len(batch)
            print(f"   lote falhou ({result['error']}): {batch}")
            continue
        for key in totals:
            totals[key] += result.get(key, 0)

    summary = f"{asset}: backfill de {total} título(s) novo(s) de {len(bonds)} -> {totals}"
    if failed_batches:
        summary += f" | lotes que falharam: {failed_batches}"
    return summary


def print_validation_report(conn) -> None:
    print("\n=== Validação final ===")
    market_count = conn.execute(text("SELECT count(*) FROM argos_market_history")).scalar()
    metrics_count = conn.execute(text("SELECT count(*) FROM argos_metrics")).scalar()
    print(f"argos_market_history: {market_count} registros")
    print(f"argos_metrics: {metrics_count} registros")

    min_date, max_date = conn.execute(
        text("SELECT min(reference_date), max(reference_date) FROM argos_market_history")
    ).one()
    print(f"reference_date: {min_date} até {max_date}")

    print("Contagem por asset:")
    for asset, count in conn.execute(
        text("SELECT asset, count(*) FROM argos_market_history GROUP BY asset ORDER BY asset")
    ):
        print(f"  {asset}: {count}")

    dupes = conn.execute(
        text(
            "SELECT source, category, asset, symbol, metric, reference_date, expiration_date, count(*) "
            "FROM argos_market_history "
            "GROUP BY source, category, asset, symbol, metric, reference_date, expiration_date "
            "HAVING count(*) > 1"
        )
    ).all()
    print(f"Duplicidades lógicas: {'nenhuma' if not dupes else dupes}")
    print(f"Última atualização disponível: {max_date}")


def main() -> None:
    validate_connection_scope()
    apply_migrations()

    start = date.today() - timedelta(days=BACKFILL_DAYS)
    end = date.today()

    with SessionLocal() as db:
        collector = MarketCollectorService(db)

        print(f"3) Backfill inicial (janela {start} a {end}, só onde ainda não houver histórico)")
        for asset in FUTURES_ASSETS:
            print(" -", backfill_futures_if_needed(db, collector, asset, start, end))
        for slug in MACRO_SERIES:
            print(" -", backfill_macro_if_needed(db, collector, slug, start, end))
        for asset in TREASURY_ASSETS:
            print(" -", backfill_treasury_if_needed(db, collector, asset, start, end))

        print("\n4) Coleta incremental (snapshot atual + gap-fill automático se necessário)")
        curve_results = collector.collect_all_futures_curves_incremental()
        macro_result = collector.collect_macro_incremental()
        treasury_results = collector.collect_all_treasury_curves_incremental()
        print("   curvas:", curve_results)
        print("   macro:", macro_result)
        print("   tesouro:", treasury_results)

        print("\n5) Calculando métricas (argos_metrics)")
        metrics_counts = MarketMetricsService(db).compute_all()
        print("   métricas:", metrics_counts)

        print_validation_report(db.connection())

    print("\nConcluído. Nenhuma credencial foi exibida acima.")


if __name__ == "__main__":
    main()
