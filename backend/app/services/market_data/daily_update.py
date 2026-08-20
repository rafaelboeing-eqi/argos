"""Job central de atualizacao diaria do dominio Mercado.

Fluxo: APIs (brapi) -> coleta -> banco (argos_market_history/argos_metrics)
-> metricas derivadas -> motor de regras (ponto de chamada preparado, ver
rules.py). Reaproveita os collectors existentes em market_collector.py -
nenhuma logica de fetch/normalizacao vive aqui.

Cada fonte (um ativo de futuros/commodities, macro, um titulo do Tesouro,
metricas, regras) roda isolada: uma exception ou um erro de brapi numa fonte
nunca impede as demais de rodar, e cada uma e registrada em
argos_collection_runs (inicio, fim, status, contagem de registros, erro).

Dois pontos de entrada usam run_daily_update():
- app/scripts/run_daily_update.py: execucao manual (desenvolvimento).
- app/scripts/run_scheduler.py: loop de longa duracao que chama isto uma vez
  por dia no horario configurado (DAILY_UPDATE_TIME, ver app/core/config.py).
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.collection_run_repository import insert_collection_run
from app.services.market_data.config import FUTURES_ASSETS, TREASURY_ASSETS
from app.services.market_data.market_collector import MarketCollectorService
from app.services.market_data.market_metrics import MarketMetricsService
from app.services.market_data.rules import run_market_rules

logger = logging.getLogger("argos.market_data.daily_update")

_COUNT_KEYS = ("created", "updated", "unchanged", "skipped")


def _run_source(db: Session, job_run_id: str, source: str, fn: Callable[[], Any]) -> dict:
    """Executa uma fonte de forma isolada e registra o resultado.

    Cobre os dois jeitos que uma fonte pode falhar hoje: uma exception
    (bug, erro de banco, etc - nunca deveria acontecer, mas nao pode derrubar
    o job) e o `{"error": ...}` que os proprios collectors retornam para
    falhas conhecidas da brapi (sem levantar exception). Em ambos os casos,
    o erro e logado e persistido, e a execucao segue para a proxima fonte.
    """
    started_at = datetime.now(UTC)
    try:
        result = fn()
        error = result.get("error") if isinstance(result, dict) else None
    except Exception as exc:  # noqa: BLE001 - deliberado: uma fonte com bug nunca deve afundar o job
        logger.exception("Fonte '%s' falhou de forma inesperada", source)
        result = None
        error = str(exc)
    finished_at = datetime.now(UTC)

    counts = {key: result.get(key) for key in _COUNT_KEYS} if isinstance(result, dict) else {}
    status = "error" if error else "success"
    if error:
        logger.error("Fonte '%s' falhou: %s", source, error)
    else:
        logger.info("Fonte '%s' concluida: %s", source, result)

    insert_collection_run(
        db,
        job_run_id=job_run_id,
        source=source,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        records_created=counts.get("created"),
        records_updated=counts.get("updated"),
        records_unchanged=counts.get("unchanged"),
        records_skipped=counts.get("skipped"),
        error=error,
    )
    db.commit()
    return {"source": source, "status": status, "result": result, "error": error}


def run_daily_update(db: Session) -> dict:
    """Roda a atualizacao diaria completa e retorna um resumo. Sempre
    termina (nunca levanta por falha de uma fonte) - inspecione
    `summary["failed_sources"]` para saber se algo precisa de atencao."""
    job_run_id = uuid.uuid4().hex
    collector = MarketCollectorService(db)
    sources_run: list[dict] = []

    for asset in FUTURES_ASSETS:
        sources_run.append(
            _run_source(
                db,
                job_run_id,
                f"futures_curve:{asset}",
                lambda a=asset: collector.collect_futures_curve_incremental(a),
            )
        )

    sources_run.append(_run_source(db, job_run_id, "macro", lambda: collector.collect_macro_incremental()))

    for asset in TREASURY_ASSETS:
        sources_run.append(
            _run_source(
                db,
                job_run_id,
                f"treasury:{asset}",
                lambda a=asset: collector.collect_treasury_curve_incremental(a),
            )
        )

    sources_run.append(_run_source(db, job_run_id, "metrics", lambda: MarketMetricsService(db).compute_all()))
    sources_run.append(_run_source(db, job_run_id, "rules", lambda: run_market_rules(db)))

    failed = [s["source"] for s in sources_run if s["status"] == "error"]
    summary = {
        "job_run_id": job_run_id,
        "sources": sources_run,
        "failed_sources": failed,
        "ok": len(failed) == 0,
    }
    logger.info(
        "run_daily_update finished (job_run_id=%s): %d/%d fontes ok",
        job_run_id,
        len(sources_run) - len(failed),
        len(sources_run),
    )
    return summary
