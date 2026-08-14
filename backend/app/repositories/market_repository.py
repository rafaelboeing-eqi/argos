"""All SQL access to argos_market_history / argos_metrics lives here.

Nothing outside this module should build a query against these two tables.
"""

from datetime import date
from typing import Any

from sqlalchemy import and_, func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.market_history import ArgosMarketHistory
from app.models.metric import ArgosMetric
from app.services.market_data.config import CATEGORY_FUTURES_CURVE

# Sentinels matching the COALESCE(...) expressions baked into the NULL-safe unique
# indexes (uq_argos_market_history_series / uq_argos_metrics_series) - must be the
# exact same expression for ON CONFLICT to resolve to that index as its arbiter.
_EXPIRATION_SENTINEL = date(1, 1, 1)
_SYMBOL_SENTINEL = ""

# Keeps each INSERT well under Postgres's ~65535 bind-parameter limit and the
# statement reasonably sized, while still batching hundreds of rows per round trip
# instead of one round trip per point.
_UPSERT_BATCH_SIZE = 500


def _dedupe_keep_last(points: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    """A single INSERT ... ON CONFLICT errors (CardinalityViolation) if two rows in
    the same statement share a conflict key - confirmed empirically. Collapse to the
    last occurrence per key (same net effect as the old apply-in-order loop)."""
    deduped: dict[tuple, dict[str, Any]] = {}
    for point in points:
        deduped[key_fn(point)] = point
    return list(deduped.values())


def _chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def bulk_upsert_market_points(db: Session, points: list[dict[str, Any] | None]) -> dict[str, int]:
    """Atomically upsert argos_market_history rows via INSERT ... ON CONFLICT,
    targeting exactly the uq_argos_market_history_series index - i.e. (source,
    category, asset, symbol, metric, reference_date, expiration_date with NULL
    coalesced to a sentinel, matching the index's own COALESCE expression).

    Race-free across concurrent processes/connections and free of any per-point
    SELECT round trip - both confirmed empirically against a real Postgres before
    this was written. `metadata` is only overwritten when the caller provides one
    (None means "keep whatever is already stored"), matching prior semantics.
    """
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    rows: list[dict[str, Any]] = []
    for point in points:
        if not point:
            counts["skipped"] += 1
            continue
        rows.append(point)

    if not rows:
        return counts

    rows = _dedupe_keep_last(
        rows,
        key_fn=lambda p: (
            p["source"],
            p["category"],
            p["asset"],
            p["symbol"],
            p["metric"],
            p["reference_date"],
            p.get("expiration_date"),
        ),
    )

    for batch in _chunks(rows, _UPSERT_BATCH_SIZE):
        # pg_insert() is given the raw Table (not the mapped class): with the mapped
        # class, SQLAlchemy's ORM-bulk-insert path resolves a string "metadata" key
        # through the mapper's entity namespace, where it collides with every
        # declarative class's own `.metadata` (the MetaData registry) instead of our
        # metadata column - confirmed empirically. The Table has no such attribute.
        stmt = pg_insert(ArgosMarketHistory.__table__).values(
            [
                {
                    "source": p["source"],
                    "category": p["category"],
                    "asset": p["asset"],
                    "symbol": p["symbol"],
                    "metric": p["metric"],
                    "value": p["value"],
                    "reference_date": p["reference_date"],
                    "expiration_date": p.get("expiration_date"),
                    "metadata": p.get("metadata"),
                }
                for p in batch
            ]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                ArgosMarketHistory.source,
                ArgosMarketHistory.category,
                ArgosMarketHistory.asset,
                ArgosMarketHistory.symbol,
                ArgosMarketHistory.metric,
                ArgosMarketHistory.reference_date,
                func.coalesce(ArgosMarketHistory.expiration_date, _EXPIRATION_SENTINEL),
            ],
            set_={
                "value": stmt.excluded.value,
                "metadata": func.coalesce(stmt.excluded.metadata, ArgosMarketHistory.extra),
            },
            where=or_(
                ArgosMarketHistory.value.is_distinct_from(stmt.excluded.value),
                and_(
                    stmt.excluded.metadata.isnot(None),
                    ArgosMarketHistory.extra.is_distinct_from(stmt.excluded.metadata),
                ),
            ),
        ).returning(ArgosMarketHistory.id, literal_column("(xmax = 0)").label("inserted"))

        returned = db.execute(stmt).all()
        created = sum(1 for row in returned if row.inserted)
        counts["created"] += created
        counts["updated"] += len(returned) - created
        counts["unchanged"] += len(batch) - len(returned)

    db.flush()
    return counts


def _expiration_filter(expiration_date: date | None):
    if expiration_date is None:
        return ArgosMarketHistory.expiration_date.is_(None)
    return ArgosMarketHistory.expiration_date == expiration_date


def get_curve(
    db: Session, asset: str, reference_date: date | None = None, category: str = CATEGORY_FUTURES_CURVE
) -> list[ArgosMarketHistory]:
    """All rows for `asset` at a given reference_date (defaults to the latest one
    available). `category` defaults to futures curves; pass CATEGORY_TREASURY for
    Tesouro Direto bonds - same "latest snapshot, one row per symbol/metric" shape."""
    if reference_date is None:
        latest_stmt = select(func.max(ArgosMarketHistory.reference_date)).where(
            ArgosMarketHistory.category == category,
            ArgosMarketHistory.asset == asset,
        )
        reference_date = db.execute(latest_stmt).scalar_one_or_none()
        if reference_date is None:
            return []

    stmt = (
        select(ArgosMarketHistory)
        .where(
            ArgosMarketHistory.category == category,
            ArgosMarketHistory.asset == asset,
            ArgosMarketHistory.reference_date == reference_date,
        )
        .order_by(ArgosMarketHistory.expiration_date.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_symbol_history(
    db: Session,
    symbol: str,
    category: str = CATEGORY_FUTURES_CURVE,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ArgosMarketHistory]:
    stmt = select(ArgosMarketHistory).where(
        ArgosMarketHistory.category == category,
        ArgosMarketHistory.symbol == symbol,
    )
    if start_date is not None:
        stmt = stmt.where(ArgosMarketHistory.reference_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ArgosMarketHistory.reference_date <= end_date)
    stmt = stmt.order_by(ArgosMarketHistory.reference_date.asc())
    return list(db.execute(stmt).scalars().all())


def get_macro_series(
    db: Session,
    slug: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = None,
) -> list[ArgosMarketHistory]:
    stmt = select(ArgosMarketHistory).where(
        ArgosMarketHistory.category == "macro",
        ArgosMarketHistory.asset == slug,
    )
    if start_date is not None:
        stmt = stmt.where(ArgosMarketHistory.reference_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ArgosMarketHistory.reference_date <= end_date)
    stmt = stmt.order_by(ArgosMarketHistory.reference_date.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_latest_reference_date(db: Session, category: str, asset: str) -> date | None:
    """Most recent reference_date already stored for this (category, asset) - used to
    detect gaps since the last successful collection run."""
    stmt = select(func.max(ArgosMarketHistory.reference_date)).where(
        ArgosMarketHistory.category == category,
        ArgosMarketHistory.asset == asset,
    )
    return db.execute(stmt).scalar_one_or_none()


def has_history_for_symbol(db: Session, category: str, symbol: str) -> bool:
    """Whether any row already exists for this (category, symbol) - used to decide
    whether a specific bond/contract still needs its initial historical backfill,
    independent of whether OTHER symbols in the same asset already have data."""
    stmt = select(ArgosMarketHistory.id).where(
        ArgosMarketHistory.category == category,
        ArgosMarketHistory.symbol == symbol,
    ).limit(1)
    return db.execute(stmt).first() is not None


def get_data_freshness(db: Session) -> date | None:
    """Most recent reference_date across every series - the honest answer to
    'what is the newest data Argos actually has right now', independent of brapi
    being reachable at this instant."""
    return db.execute(select(func.max(ArgosMarketHistory.reference_date))).scalar_one_or_none()


def get_value_on_or_before(
    db: Session, category: str, asset: str, symbol: str, metric: str, as_of: date
) -> ArgosMarketHistory | None:
    """Most recent point at or before `as_of` - used for 1d/7d/30d/90d variation lookups."""
    stmt = (
        select(ArgosMarketHistory)
        .where(
            ArgosMarketHistory.category == category,
            ArgosMarketHistory.asset == asset,
            ArgosMarketHistory.symbol == symbol,
            ArgosMarketHistory.metric == metric,
            ArgosMarketHistory.reference_date <= as_of,
        )
        .order_by(ArgosMarketHistory.reference_date.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def bulk_upsert_metrics(db: Session, points: list[dict[str, Any] | None]) -> dict[str, int]:
    """Same atomic INSERT ... ON CONFLICT strategy as bulk_upsert_market_points,
    targeting uq_argos_metrics_series - (category, asset, symbol with NULL coalesced
    to '', metric, reference_date)."""
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    rows: list[dict[str, Any]] = []
    for point in points:
        if not point:
            counts["skipped"] += 1
            continue
        rows.append(point)

    if not rows:
        return counts

    rows = _dedupe_keep_last(
        rows,
        key_fn=lambda p: (
            p["category"],
            p["asset"],
            p.get("symbol"),
            p["metric"],
            p["reference_date"],
        ),
    )

    for batch in _chunks(rows, _UPSERT_BATCH_SIZE):
        # See bulk_upsert_market_points: pg_insert() needs the raw Table, not the
        # mapped class, to avoid the "metadata" entity-namespace collision.
        stmt = pg_insert(ArgosMetric.__table__).values(
            [
                {
                    "source": p["source"],
                    "category": p["category"],
                    "asset": p["asset"],
                    "symbol": p.get("symbol"),
                    "metric": p["metric"],
                    "value": p["value"],
                    "reference_date": p["reference_date"],
                    "metadata": p.get("metadata"),
                }
                for p in batch
            ]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                ArgosMetric.category,
                ArgosMetric.asset,
                func.coalesce(ArgosMetric.symbol, _SYMBOL_SENTINEL),
                ArgosMetric.metric,
                ArgosMetric.reference_date,
            ],
            set_={
                "value": stmt.excluded.value,
                "metadata": func.coalesce(stmt.excluded.metadata, ArgosMetric.extra),
                "updated_at": func.now(),
            },
            where=or_(
                ArgosMetric.value.is_distinct_from(stmt.excluded.value),
                and_(
                    stmt.excluded.metadata.isnot(None),
                    ArgosMetric.extra.is_distinct_from(stmt.excluded.metadata),
                ),
            ),
        ).returning(ArgosMetric.id, literal_column("(xmax = 0)").label("inserted"))

        returned = db.execute(stmt).all()
        created = sum(1 for row in returned if row.inserted)
        counts["created"] += created
        counts["updated"] += len(returned) - created
        counts["unchanged"] += len(batch) - len(returned)

    db.flush()
    return counts


def get_latest_metrics(
    db: Session, category: str | None = None, asset: str | None = None
) -> list[ArgosMetric]:
    stmt = select(ArgosMetric)
    if category is not None:
        stmt = stmt.where(ArgosMetric.category == category)
    if asset is not None:
        stmt = stmt.where(ArgosMetric.asset == asset)
    stmt = stmt.order_by(ArgosMetric.reference_date.desc())
    return list(db.execute(stmt).scalars().all())
