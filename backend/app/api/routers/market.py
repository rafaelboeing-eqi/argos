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
)
from app.services.market_data.config import FUTURES_ASSETS, MACRO_SERIES
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
