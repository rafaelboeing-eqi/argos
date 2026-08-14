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
    change_90d: float | None
    reference_date: date | None


class MarketOverviewResponse(BaseModel):
    indicators: list[IndicatorCard]
    commodities: list[CommodityCard]
    data_as_of: date | None


class RateCurvePoint(BaseModel):
    symbol: str
    expiration_date: date
    reference_date: date
    time_to_maturity_years: float
    value: float


class RateCurveViewResponse(BaseModel):
    asset: str
    curves: dict[str, list[RateCurvePoint]]


class TreasuryCurvePoint(BaseModel):
    symbol: str
    expiration_date: date
    reference_date: date
    time_to_maturity_years: float
    bond_type: str | None
    coupon_type: str | None
    buy_rate: float | None
    sell_rate: float | None


class TreasuryCurveViewResponse(BaseModel):
    asset: str
    coupon_types: list[str]
    curves: dict[str, list[TreasuryCurvePoint]]


class TreasuryBondHistoryPoint(BaseModel):
    reference_date: date
    buy_rate: float | None
    sell_rate: float | None
    buy_price: float | None


class TreasuryBondHistoryResponse(BaseModel):
    symbol: str
    asset: str | None
    bond_type: str | None
    coupon_type: str | None
    expiration_date: date | None
    rate_type: str | None
    current_buy_rate: float | None
    current_reference_date: date | None
    variation_bps: dict[str, float | None]
    points: list[TreasuryBondHistoryPoint]


class CommodityHistoryPoint(BaseModel):
    reference_date: date
    value: float


class CommodityHistoryResponse(BaseModel):
    asset: str
    symbol: str | None
    points: list[CommodityHistoryPoint]
