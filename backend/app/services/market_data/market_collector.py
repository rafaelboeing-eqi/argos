"""Fetches market data from brapi, normalizes it, and persists it to argos_market_history."""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.brapi_provider import BrapiProvider
from app.services.market_data.config import FUTURES_ASSETS, MACRO_SERIES
from app.services.market_data.exceptions import BrapiError
from app.services.market_data.normalizers import (
    normalize_futures_curve_contract,
    normalize_futures_history_point,
    normalize_macro_observation,
)

logger = logging.getLogger("argos.market_data.collector")


class MarketCollectorService:
    def __init__(self, db: Session, provider: BrapiProvider | None = None):
        self.db = db
        self.provider = provider or BrapiProvider()

    def collect_futures_curve(self, asset: str) -> dict:
        """Fetch and persist the current term structure for one futures asset."""
        try:
            payload = self.provider.get_futures_term_structure(asset)
        except BrapiError as exc:
            logger.error("Failed to collect futures curve for %s: %s", asset, exc)
            return {"asset": asset, "error": str(exc)}

        points = [normalize_futures_curve_contract(asset, contract) for contract in payload.get("contracts", [])]
        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        return {"asset": asset, **counts}

    def collect_all_futures_curves(self) -> list[dict]:
        return [self.collect_futures_curve(asset) for asset in FUTURES_ASSETS]

    def collect_macro_latest(self, symbols: list[str] | None = None) -> dict:
        """Fetch and persist the latest observation for each configured macro series.

        Intended for the daily job - use collect_macro_history() for backfill instead.
        """
        series = symbols or MACRO_SERIES
        try:
            payload = self.provider.get_macro_latest(symbols=series)
        except BrapiError as exc:
            logger.error("Failed to collect macro latest: %s", exc)
            return {"series": series, "error": str(exc)}

        points = []
        for entry in payload.get("results", []):
            series_meta = entry.get("series") or {}
            slug = series_meta.get("slug")
            latest = entry.get("latest")
            if not slug or not latest:
                continue
            points.append(normalize_macro_observation(slug, series_meta, latest))

        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        return {"series": series, **counts}

    def collect_futures_history(
        self,
        asset: str,
        symbol: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        sort_order: str = "asc",
    ) -> dict:
        """Backfill: fetch the full daily history for one contract symbol."""
        try:
            payload = self.provider.get_futures_historical(
                symbol,
                start_date=str(start_date) if start_date else None,
                end_date=str(end_date) if end_date else None,
                sort_order=sort_order,
            )
        except BrapiError as exc:
            logger.error("Failed to collect futures history for %s: %s", symbol, exc)
            return {"symbol": symbol, "error": str(exc)}

        future_meta = payload.get("future") or {}
        points = [
            normalize_futures_history_point(asset, future_meta, point)
            for point in future_meta.get("history", [])
        ]
        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        return {"symbol": symbol, **counts}

    def collect_macro_history(
        self,
        symbols: list[str] | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        sort_order: str = "asc",
        limit: int | None = None,
    ) -> dict:
        """Backfill: fetch the full history for the configured macro series."""
        series = symbols or MACRO_SERIES
        try:
            payload = self.provider.get_macro(
                series,
                start_date=str(start_date) if start_date else None,
                end_date=str(end_date) if end_date else None,
                sort_order=sort_order,
                limit=limit,
            )
        except BrapiError as exc:
            logger.error("Failed to collect macro history: %s", exc)
            return {"series": series, "error": str(exc)}

        points = []
        for entry in payload.get("results", []):
            series_meta = entry.get("series") or {}
            slug = series_meta.get("slug")
            if not slug:
                continue
            for observation in entry.get("observations", []):
                points.append(normalize_macro_observation(slug, series_meta, observation))

        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        return {"series": series, **counts}

    def discover_curve_symbols(self, asset: str) -> list[str]:
        """Symbols currently quoted for `asset`'s curve - used by the backfill script
        to know which contracts to fetch history for."""
        try:
            payload = self.provider.get_futures_term_structure(asset)
        except BrapiError as exc:
            logger.error("Failed to discover curve symbols for %s: %s", asset, exc)
            return []
        return [c["symbol"] for c in payload.get("contracts", []) if c.get("symbol")]
