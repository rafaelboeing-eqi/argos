"""Fetches market data from brapi, normalizes it, and persists it to argos_market_history."""

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories.market_repository import bulk_upsert_market_points, get_latest_reference_date
from app.services.market_data.brapi_provider import BrapiProvider
from app.services.market_data.config import (
    CATEGORY_FUTURES_CURVE,
    CATEGORY_MACRO,
    CATEGORY_TREASURY,
    FUTURES_ASSETS,
    MACRO_SERIES,
    TREASURY_ASSETS,
    TREASURY_BOND_TYPE_PREFIXES,
    TREASURY_HISTORY_BATCH_SIZE,
    TREASURY_LIST_LIMIT,
)
from app.services.market_data.exceptions import BrapiError
from app.services.market_data.normalizers import (
    normalize_futures_curve_contract,
    normalize_futures_history_point,
    normalize_macro_observation,
    normalize_treasury_history_point,
    normalize_treasury_point,
)

logger = logging.getLogger("argos.market_data.collector")

# brapi's GET /api/v2/macro defaults to limit=20 when the param is omitted,
# which silently truncates any backfill spanning more than ~20 observations.
# Always pass an explicit, generous limit so a date range is never cut short.
DEFAULT_MACRO_HISTORY_LIMIT = 5000


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

    def collect_futures_curve_incremental(self, asset: str) -> dict:
        """Daily-job entry point: always grab today's snapshot (one cheap call), and if the
        last run was missed for more than a day, backfill exactly the missing window per
        contract so the gap in argos_market_history gets filled instead of silently skipped.
        """
        previous_last_date = get_latest_reference_date(self.db, CATEGORY_FUTURES_CURVE, asset)

        try:
            payload = self.provider.get_futures_term_structure(asset)
        except BrapiError as exc:
            logger.error("Failed to collect futures curve for %s: %s", asset, exc)
            return {"asset": asset, "mode": "snapshot", "error": str(exc)}

        contracts = payload.get("contracts", [])
        points = [normalize_futures_curve_contract(asset, contract) for contract in contracts]
        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        result = {"asset": asset, "mode": "snapshot", **counts}

        today = date.today()
        if previous_last_date is not None and (today - previous_last_date).days > 1:
            gap_start = previous_last_date + timedelta(days=1)
            gap_end = today - timedelta(days=1)  # today itself was just covered by the snapshot above
            symbols = [c["symbol"] for c in contracts if c.get("symbol")]
            result["gap_fill"] = self._backfill_futures_gap(asset, symbols, gap_start, gap_end)

        return result

    def collect_all_futures_curves_incremental(self) -> list[dict]:
        return [self.collect_futures_curve_incremental(asset) for asset in FUTURES_ASSETS]

    def _backfill_futures_gap(self, asset: str, symbols: list[str], start: date, end: date) -> dict:
        totals = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        errors = []
        for symbol in symbols:
            result = self.collect_futures_history(asset, symbol, start_date=start, end_date=end)
            if "error" in result:
                errors.append({"symbol": symbol, "error": result["error"]})
                continue
            for key in totals:
                totals[key] += result.get(key, 0)
        summary = {"from": str(start), "to": str(end), **totals}
        if errors:
            summary["errors"] = errors
        return summary

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

    def collect_macro_incremental(self, symbols: list[str] | None = None) -> dict:
        """Daily-job entry point: always grab the latest published value for each series
        (one cheap call), and for any slug whose last stored day is more than a day old,
        backfill exactly the missing window instead of silently losing those observations.
        """
        series = symbols or MACRO_SERIES
        # Snapshot each slug's last known date BEFORE collect_macro_latest() writes today's
        # value - otherwise the gap check below would see today's just-inserted row and
        # always conclude "no gap", even when days were actually missed.
        previous_last_dates = {slug: get_latest_reference_date(self.db, CATEGORY_MACRO, slug) for slug in series}

        result = self.collect_macro_latest(symbols=series)
        result["mode"] = "latest"
        if "error" in result:
            return result

        today = date.today()
        gap_totals = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        gap_windows: dict[str, dict] = {}
        for slug in series:
            previous_last_date = previous_last_dates[slug]
            if previous_last_date is None or (today - previous_last_date).days <= 1:
                continue
            gap_start = previous_last_date + timedelta(days=1)
            gap_end = today - timedelta(days=1)
            hist_result = self.collect_macro_history(symbols=[slug], start_date=gap_start, end_date=gap_end)
            if "error" in hist_result:
                gap_windows[slug] = {"from": str(gap_start), "to": str(gap_end), "error": hist_result["error"]}
                continue
            for key in gap_totals:
                gap_totals[key] += hist_result.get(key, 0)
            gap_windows[slug] = {"from": str(gap_start), "to": str(gap_end)}

        if gap_windows:
            result["gap_fill"] = {"series": gap_windows, **gap_totals}

        return result

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
                limit=limit if limit is not None else DEFAULT_MACRO_HISTORY_LIMIT,
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

    # -- Tesouro Direto ---------------------------------------------------

    def discover_treasury_bonds(self, asset: str) -> list[dict]:
        """Every currently-listed bond whose bondType matches `asset` (see
        TREASURY_BOND_TYPE_PREFIXES) - filtering by brapi's own `indexer` field
        isn't enough, since e.g. indexer=ipca also covers Tesouro Educa+ and
        Tesouro Renda+, which are out of scope. Each bond already carries its
        own current snapshot (buyRate/sellRate/buyPrice/sellPrice/basePrice).
        """
        try:
            payload = self.provider.get_treasury_list(limit=TREASURY_LIST_LIMIT)
        except BrapiError as exc:
            logger.error("Failed to discover treasury bonds for %s: %s", asset, exc)
            return []
        prefix = TREASURY_BOND_TYPE_PREFIXES[asset]
        return [bond for bond in payload.get("results", []) if (bond.get("bondType") or "").startswith(prefix)]

    def collect_treasury_curve(self, asset: str) -> dict:
        """Fetch and persist the current snapshot for every bond of this treasury asset."""
        bonds = self.discover_treasury_bonds(asset)
        points = []
        for bond in bonds:
            points.extend(normalize_treasury_point(asset, bond))
        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        return {"asset": asset, **counts}

    def collect_all_treasury_curves(self) -> list[dict]:
        return [self.collect_treasury_curve(asset) for asset in TREASURY_ASSETS]

    def collect_treasury_curve_incremental(self, asset: str) -> dict:
        """Daily-job entry point, mirrors collect_futures_curve_incremental(): always
        grab today's snapshot (one cheap call), and if the last run was missed for
        more than a day, backfill exactly the missing window per bond."""
        previous_last_date = get_latest_reference_date(self.db, CATEGORY_TREASURY, asset)
        bonds = self.discover_treasury_bonds(asset)
        if not bonds:
            return {"asset": asset, "mode": "snapshot", "error": "no bonds found on brapi right now"}

        points = []
        for bond in bonds:
            points.extend(normalize_treasury_point(asset, bond))
        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        result = {"asset": asset, "mode": "snapshot", **counts}

        today = date.today()
        if previous_last_date is not None and (today - previous_last_date).days > 1:
            gap_start = previous_last_date + timedelta(days=1)
            gap_end = today - timedelta(days=1)
            symbols = [bond["symbol"] for bond in bonds if bond.get("symbol")]
            result["gap_fill"] = self._backfill_treasury_gap(asset, symbols, gap_start, gap_end)

        return result

    def collect_all_treasury_curves_incremental(self) -> list[dict]:
        return [self.collect_treasury_curve_incremental(asset) for asset in TREASURY_ASSETS]

    def _backfill_treasury_gap(self, asset: str, symbols: list[str], start: date, end: date) -> dict:
        totals = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        errors = []
        for batch in chunked(symbols, TREASURY_HISTORY_BATCH_SIZE):
            result = self.collect_treasury_history(asset, batch, start_date=start, end_date=end)
            if "error" in result:
                errors.append({"symbols": batch, "error": result["error"]})
                continue
            for key in totals:
                totals[key] += result.get(key, 0)
        summary = {"from": str(start), "to": str(end), **totals}
        if errors:
            summary["errors"] = errors
        return summary

    def collect_treasury_history(
        self,
        asset: str,
        symbols: list[str],
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        sort_order: str = "asc",
    ) -> dict:
        """Backfill: fetch daily history for up to ~20 bond symbols in one call."""
        try:
            payload = self.provider.get_treasury_indicators_history(
                symbols,
                start_date=str(start_date) if start_date else None,
                end_date=str(end_date) if end_date else None,
                sort_order=sort_order,
            )
        except BrapiError as exc:
            logger.error("Failed to collect treasury history for %s: %s", symbols, exc)
            return {"symbols": symbols, "error": str(exc)}

        points = []
        for entry in payload.get("results", []):
            bond_meta = {key: value for key, value in entry.items() if key != "history"}
            for observation in entry.get("history", []):
                points.extend(normalize_treasury_history_point(asset, bond_meta, observation))

        counts = bulk_upsert_market_points(self.db, points)
        self.db.commit()
        return {"symbols": symbols, **counts}


def chunked(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]
