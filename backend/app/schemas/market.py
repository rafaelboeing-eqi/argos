from datetime import date

from pydantic import BaseModel


class CurvePoint(BaseModel):
    symbol: str
    metric: str
    value: float
    reference_date: date
    expiration_date: date | None
    metadata: dict | None = None


class CurveResponse(BaseModel):
    asset: str
    reference_date: date | None
    points: list[CurvePoint]


class HistoryPoint(BaseModel):
    metric: str
    value: float
    reference_date: date
    metadata: dict | None = None


class HistoryResponse(BaseModel):
    symbol: str
    points: list[HistoryPoint]


class MacroObservation(BaseModel):
    value: float
    reference_date: date


class MacroSeriesResponse(BaseModel):
    slug: str
    points: list[MacroObservation]


class MacroResponse(BaseModel):
    series: list[MacroSeriesResponse]


class MetricPoint(BaseModel):
    category: str
    asset: str
    symbol: str | None
    metric: str
    value: float
    reference_date: date
    metadata: dict | None = None


class MetricsResponse(BaseModel):
    metrics: list[MetricPoint]


class IndicatorCard(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str | None
    reference_date: date | None


class CommodityCard(BaseModel):
    asset: str
    label: str
    symbol: str | None
    value: float | None
    change_1d: float | None
    change_7d: float | None
    change_30d: float | None
    reference_date: date | None


class MarketOverviewResponse(BaseModel):
    indicators: list[IndicatorCard]
    commodities: list[CommodityCard]
