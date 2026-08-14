export type IndicatorCard = {
  key: string;
  label: string;
  value: number | null;
  unit: string | null;
  reference_date: string | null;
};

export type CommodityCard = {
  asset: string;
  label: string;
  symbol: string | null;
  value: number | null;
  change_1d: number | null;
  change_7d: number | null;
  change_30d: number | null;
  change_90d: number | null;
  reference_date: string | null;
};

export type MarketOverview = {
  indicators: IndicatorCard[];
  commodities: CommodityCard[];
  data_as_of: string | null;
};

export type CurvePoint = {
  symbol: string;
  metric: string;
  value: number;
  reference_date: string;
  expiration_date: string | null;
  metadata: Record<string, unknown> | null;
};

export type CurveResponse = {
  asset: string;
  reference_date: string | null;
  points: CurvePoint[];
};

export type HistoryPoint = {
  metric: string;
  value: number;
  reference_date: string;
  metadata: Record<string, unknown> | null;
};

export type HistoryResponse = {
  symbol: string;
  points: HistoryPoint[];
};

export const RATE_CURVE_ASSETS = ["DI1", "DAP"] as const;
export type RateCurveAsset = (typeof RATE_CURVE_ASSETS)[number];

export const CURVE_WINDOWS = ["today", "7d", "30d", "90d"] as const;
export type CurveWindowLabel = (typeof CURVE_WINDOWS)[number];

export const CURVE_WINDOW_LABELS: Record<CurveWindowLabel, string> = {
  today: "Hoje",
  "7d": "7D",
  "30d": "30D",
  "90d": "90D",
};

export type RateCurvePoint = {
  symbol: string;
  expiration_date: string;
  reference_date: string;
  value: number;
};

export type RateCurveViewResponse = {
  asset: string;
  curves: Record<CurveWindowLabel, RateCurvePoint[]>;
};

export const TREASURY_ASSETS = ["treasury_ipca", "treasury_prefixado", "treasury_selic"] as const;
export type TreasuryAsset = (typeof TREASURY_ASSETS)[number];

export const TREASURY_LABELS: Record<TreasuryAsset, string> = {
  treasury_ipca: "Tesouro IPCA+",
  treasury_prefixado: "Tesouro Prefixado",
  treasury_selic: "Tesouro Selic",
};

export const TREASURY_IS_REAL_RATE: Record<TreasuryAsset, boolean> = {
  treasury_ipca: true,
  treasury_prefixado: false,
  treasury_selic: false,
};

export const TREASURY_COUPON_TYPE_LABELS: Record<string, string> = {
  zero: "Cupom zero",
  semestral: "Com juros semestrais",
};

export type TreasuryCurvePoint = {
  symbol: string;
  expiration_date: string;
  reference_date: string;
  bond_type: string | null;
  coupon_type: string | null;
  buy_rate: number | null;
  sell_rate: number | null;
};

export type TreasuryCurveViewResponse = {
  asset: string;
  coupon_types: string[];
  curves: Record<CurveWindowLabel, TreasuryCurvePoint[]>;
};

export const COMMODITY_ASSETS = ["BGI", "CCM", "ICF", "SJC"] as const;
export type CommodityAsset = (typeof COMMODITY_ASSETS)[number];

export const COMMODITY_HISTORY_PERIODS = ["30d", "90d", "6m", "1a"] as const;
export type CommodityHistoryPeriod = (typeof COMMODITY_HISTORY_PERIODS)[number];

export const COMMODITY_HISTORY_PERIOD_LABELS: Record<CommodityHistoryPeriod, string> = {
  "30d": "30D",
  "90d": "90D",
  "6m": "6M",
  "1a": "1A",
};

export type CommodityHistoryPoint = {
  reference_date: string;
  value: number;
};

export type CommodityHistoryApiResponse = {
  asset: string;
  symbol: string | null;
  points: CommodityHistoryPoint[];
};
