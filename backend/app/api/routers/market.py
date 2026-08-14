from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.market_repository import (
    get_curve,
    get_latest_metrics,
    get_macro_series,
    get_symbol_history,
)
from app.schemas.market import (
    CommodityHistoryPoint,
    CommodityHistoryResponse,
    CurvePoint,
    CurveResponse,
    HistoryPoint,
    HistoryResponse,
    MacroObservation,
    MacroResponse,
    MacroSeriesResponse,
    MarketOverviewResponse,
    MetricPoint,
    MetricsResponse,
    RateCurvePoint,
    RateCurveViewResponse,
    TreasuryCurvePoint,
    TreasuryCurveViewResponse,
)
from app.services.market_data.commodity_history import PERIOD_DAYS, build_commodity_history_view
from app.services.market_data.config import COMMODITY_ASSETS, FUTURES_ASSETS, MACRO_SERIES, RATE_CURVE_ASSETS, TREASURY_ASSETS
from app.services.market_data.curve_view import build_rate_curve_view, build_treasury_curve_view
from app.services.market_data.overview import build_overview

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview", response_model=MarketOverviewResponse)
def read_overview(db: Session = Depends(get_db)) -> MarketOverviewResponse:
    return MarketOverviewResponse(**build_overview(db))


@router.get("/futures/{asset}/curve", response_model=CurveResponse)
def read_futures_curve(asset: str, db: Session = Depends(get_db)) -> CurveResponse:
    if asset not in FUTURES_ASSETS:
        raise HTTPException(status_code=404, detail=f"Unknown futures asset '{asset}'")

    contracts = get_curve(db, asset)
    points = [
        CurvePoint(
            symbol=c.symbol,
            metric=c.metric,
            value=float(c.value),
            reference_date=c.reference_date,
            expiration_date=c.expiration_date,
            metadata=c.extra,
        )
        for c in contracts
    ]
    reference_date = contracts[0].reference_date if contracts else None
    return CurveResponse(asset=asset, reference_date=reference_date, points=points)


@router.get("/futures/{asset}/rate-curve", response_model=RateCurveViewResponse)
def read_rate_curve_view(asset: str, db: Session = Depends(get_db)) -> RateCurveViewResponse:
    """DI/DAP chart data: one contract per year, compared across today/7d/30d/90d."""
    if asset not in RATE_CURVE_ASSETS:
        raise HTTPException(status_code=404, detail=f"'{asset}' is not a rate curve asset")

    view = build_rate_curve_view(db, asset)
    curves = {
        label: [RateCurvePoint(**point) for point in points] for label, points in view["curves"].items()
    }
    return RateCurveViewResponse(asset=asset, curves=curves)


@router.get("/futures/{symbol}/history", response_model=HistoryResponse)
def read_futures_history(
    symbol: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    rows = get_symbol_history(db, symbol, start_date=start_date, end_date=end_date)
    points = [
        HistoryPoint(metric=r.metric, value=float(r.value), reference_date=r.reference_date, metadata=r.extra)
        for r in rows
    ]
    return HistoryResponse(symbol=symbol, points=points)


@router.get("/macro", response_model=MacroResponse)
def read_macro(
    slugs: str | None = Query(default=None, description="Comma-separated slugs, defaults to all configured series"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> MacroResponse:
    series = [slug.strip() for slug in slugs.split(",")] if slugs else MACRO_SERIES
    result = []
    for slug in series:
        rows = get_macro_series(db, slug, start_date=start_date, end_date=end_date, limit=limit)
        points = [MacroObservation(value=float(r.value), reference_date=r.reference_date) for r in rows]
        result.append(MacroSeriesResponse(slug=slug, points=points))
    return MacroResponse(series=result)


@router.get("/metrics", response_model=MetricsResponse)
def read_metrics(
    category: str | None = Query(default=None),
    asset: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MetricsResponse:
    rows = get_latest_metrics(db, category=category, asset=asset)
    if symbol is not None:
        rows = [row for row in rows if row.symbol == symbol]
    points = [
        MetricPoint(
            category=r.category,
            asset=r.asset,
            symbol=r.symbol,
            metric=r.metric,
            value=float(r.value),
            reference_date=r.reference_date,
            metadata=r.extra,
        )
        for r in rows
    ]
    return MetricsResponse(metrics=points)


@router.get("/treasury/{asset}/curve", response_model=TreasuryCurveViewResponse)
def read_treasury_curve_view(
    asset: str,
    coupon_type: str | None = Query(default=None, description="Filter to one couponType (e.g. 'zero', 'semestral')"),
    db: Session = Depends(get_db),
) -> TreasuryCurveViewResponse:
    """Tesouro Direto chart data: every currently-listed bond of `asset`, by
    maturity, compared across today/7d/30d/90d. Bonds with a different
    couponType are never silently mixed - `coupon_types` lists what's
    available so the frontend can offer a modality selector."""
    if asset not in TREASURY_ASSETS:
        raise HTTPException(status_code=404, detail=f"Unknown treasury asset '{asset}'")

    view = build_treasury_curve_view(db, asset, coupon_type=coupon_type)
    curves = {
        label: [TreasuryCurvePoint(**point) for point in points] for label, points in view["curves"].items()
    }
    return TreasuryCurveViewResponse(asset=asset, coupon_types=view["coupon_types"], curves=curves)


@router.get("/commodities/{asset}/history", response_model=CommodityHistoryResponse)
def read_commodity_history(
    asset: str,
    period: str = Query(default="90d", description="One of: 30d, 90d, 6m, 1a"),
    db: Session = Depends(get_db),
) -> CommodityHistoryResponse:
    """Resolves the representative (front) contract for `asset` and returns its
    price history for the requested window - if less history is stored than
    requested, this returns whatever is available instead of erroring."""
    if asset not in COMMODITY_ASSETS:
        raise HTTPException(status_code=404, detail=f"Unknown commodity asset '{asset}'")
    if period not in PERIOD_DAYS:
        raise HTTPException(status_code=422, detail=f"Invalid period '{period}', expected one of {list(PERIOD_DAYS)}")

    view = build_commodity_history_view(db, asset, period)
    points = [CommodityHistoryPoint(**point) for point in view["points"]]
    return CommodityHistoryResponse(asset=asset, symbol=view["symbol"], points=points)
