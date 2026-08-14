"""All SQL access to argos_market_history / argos_metrics lives here.

Nothing outside this module should build a query against these two tables.
"""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.market_history import ArgosMarketHistory
from app.models.metric import ArgosMetric
from app.services.market_data.config import CATEGORY_FUTURES_CURVE


def _expiration_filter(expiration_date: date | None):
    if expiration_date is None:
        return ArgosMarketHistory.expiration_date.is_(None)
    return ArgosMarketHistory.expiration_date == expiration_date


def upsert_market_point(db: Session, point: dict[str, Any]) -> str:
    """Insert a market_history row, or update it in place if the same
    (source, category, asset, symbol, metric, reference_date, expiration_date)
    already exists. Returns "created", "updated" or "unchanged"."""
    stmt = select(ArgosMarketHistory).where(
        ArgosMarketHistory.source == point["source"],
        ArgosMarketHistory.category == point["category"],
        ArgosMarketHistory.asset == point["asset"],
        ArgosMarketHistory.symbol == point["symbol"],
        ArgosMarketHistory.metric == point["metric"],
        ArgosMarketHistory.reference_date == point["reference_date"],
        _expiration_filter(point.get("expiration_date")),
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is not None:
        changed = False
        if float(existing.value) != float(point["value"]):
            existing.value = point["value"]
            changed = True
        metadata = point.get("metadata")
        if metadata is not None and existing.extra != metadata:
            existing.extra = metadata
            changed = True
        return "updated" if changed else "unchanged"

    db.add(
        ArgosMarketHistory(
            source=point["source"],
            category=point["category"],
            asset=point["asset"],
            symbol=point["symbol"],
            metric=point["metric"],
            value=point["value"],
            reference_date=point["reference_date"],
            expiration_date=point.get("expiration_date"),
            extra=point.get("metadata"),
        )
    )
    return "created"


def bulk_upsert_market_points(db: Session, points: list[dict[str, Any] | None]) -> dict[str, int]:
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for point in points:
        if not point:
            counts["skipped"] += 1
            continue
        status = upsert_market_point(db, point)
        counts[status] += 1
    db.flush()
    return counts


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
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ArgosMarketHistory]:
    stmt = select(ArgosMarketHistory).where(
        ArgosMarketHistory.category == CATEGORY_FUTURES_CURVE,
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


def upsert_metric(db: Session, point: dict[str, Any]) -> str:
    """Insert/update an argos_metrics row keyed by (category, asset, symbol, metric, reference_date)."""
    stmt = select(ArgosMetric).where(
        ArgosMetric.category == point["category"],
        ArgosMetric.asset == point["asset"],
        ArgosMetric.symbol == point.get("symbol"),
        ArgosMetric.metric == point["metric"],
        ArgosMetric.reference_date == point["reference_date"],
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is not None:
        changed = False
        if float(existing.value) != float(point["value"]):
            existing.value = point["value"]
            changed = True
        metadata = point.get("metadata")
        if metadata is not None and existing.extra != metadata:
            existing.extra = metadata
            changed = True
        return "updated" if changed else "unchanged"

    db.add(
        ArgosMetric(
            source=point["source"],
            category=point["category"],
            asset=point["asset"],
            symbol=point.get("symbol"),
            metric=point["metric"],
            value=point["value"],
            reference_date=point["reference_date"],
            extra=point.get("metadata"),
        )
    )
    return "created"


def bulk_upsert_metrics(db: Session, points: list[dict[str, Any] | None]) -> dict[str, int]:
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for point in points:
        if not point:
            counts["skipped"] += 1
            continue
        status = upsert_metric(db, point)
        counts[status] += 1
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
