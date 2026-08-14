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
