"use client";

import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { buildCurveSeries } from "@/lib/curves";
import { formatBps, formatDate, formatShortDate, formatYearsToMaturity } from "@/lib/format";
import {
  CURVE_WINDOW_LABELS,
  CURVE_WINDOWS,
  TREASURY_ASSETS,
  TREASURY_BOND_HISTORY_PERIODS,
  TREASURY_BOND_HISTORY_PERIOD_LABELS,
  TREASURY_COUPON_TYPE_LABELS,
  TREASURY_LABELS,
  TREASURY_RATE_KIND,
  TREASURY_RATE_KIND_LABELS,
  type CurveWindowLabel,
  type TreasuryAsset,
  type TreasuryBondHistoryPeriod,
  type TreasuryBondHistoryResponse,
  type TreasuryBondOption,
  type TreasuryCurvePoint,
  type TreasuryCurveViewResponse,
} from "@/types/market";
import { EmptyState } from "./EmptyState";

const WINDOW_COLORS: Record<CurveWindowLabel, string> = {
  today: "#00C796",
  "7d": "#009E76",
  "30d": "#005D47",
  "90d": "#A8D5C6",
};

type ChartMode = "curve" | "history";

export function TreasuryCurveChart() {
  const [asset, setAsset] = useState<TreasuryAsset>("treasury_ipca");
  const [couponType, setCouponType] = useState<string | null>(null);
  const [mode, setMode] = useState<ChartMode>("curve");

  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-argos-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-argos-950">Tesouro Direto</h2>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1 rounded-full bg-argos-50 p-1">
            {(["curve", "history"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setMode(option)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  mode === option ? "bg-argos-400 text-white" : "text-argos-600 hover:text-argos-800"
                }`}
              >
                {option === "curve" ? "Curva" : "Histórico"}
              </button>
            ))}
          </div>
          <select
            value={asset}
            onChange={(event) => {
              setAsset(event.target.value as TreasuryAsset);
              setCouponType(null);
            }}
            className="rounded-full border border-argos-100 bg-argos-50 px-3 py-1 text-xs font-medium text-argos-800"
          >
            {TREASURY_ASSETS.map((option) => (
              <option key={option} value={option}>
                {TREASURY_LABELS[option]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="text-xs text-argos-500">{TREASURY_RATE_KIND_LABELS[TREASURY_RATE_KIND[asset]]}.</p>

      {mode === "curve" ? (
        // key remounts the body on asset change, resetting loading/data via initial state.
        <TreasuryCurveChartBody key={asset} asset={asset} couponType={couponType} onCouponTypeChange={setCouponType} />
      ) : (
        <TreasuryBondHistoryChart key={asset} asset={asset} />
      )}
    </section>
  );
}

function TreasuryCurveChartBody({
  asset,
  couponType,
  onCouponTypeChange,
}: {
  asset: TreasuryAsset;
  couponType: string | null;
  onCouponTypeChange: (couponType: string | null) => void;
}) {
  const [curveView, setCurveView] = useState<TreasuryCurveViewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [hiddenWindows, setHiddenWindows] = useState<Set<CurveWindowLabel>>(new Set());

  useEffect(() => {
    let cancelled = false;
    const query = couponType ? `?coupon_type=${encodeURIComponent(couponType)}` : "";
    fetchJson<TreasuryCurveViewResponse>(`/api/market/treasury/${asset}/curve${query}`)
      .then((data) => {
        if (!cancelled) setCurveView(data);
      })
      .catch(() => {
        if (!cancelled) setCurveView(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [asset, couponType]);

  const toggleWindow = (window: CurveWindowLabel) => {
    setHiddenWindows((prev) => {
      const next = new Set(prev);
      if (next.has(window)) next.delete(window);
      else next.add(window);
      return next;
    });
  };

  const curves = curveView?.curves;
  const couponTypes = curveView?.coupon_types ?? [];
  // Memoized for the same reason as RateCurveChart: stable references keep
  // Recharts from restarting the line-draw animation on every hover re-render.
  // Called unconditionally (before the loading early-return) per rules of hooks.
  const series = useMemo(
    () =>
      curves
        ? buildCurveSeries(
            curves,
            (point) => point.time_to_maturity_years,
            (point) => point.buy_rate
          )
        : null,
    [curves]
  );
  const hasAnyPoint = series ? CURVE_WINDOWS.some((window) => series[window].length > 0) : false;

  if (loading) {
    return <div className="h-72 animate-pulse rounded-xl bg-argos-50" />;
  }

  return (
    <div className="flex flex-col gap-3">
      {couponTypes.length > 1 && (
        <div className="flex gap-1 self-start rounded-full bg-argos-50 p-1">
          <button
            type="button"
            onClick={() => onCouponTypeChange(null)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              couponType === null ? "bg-argos-400 text-white" : "text-argos-600 hover:text-argos-800"
            }`}
          >
            Todas as modalidades
          </button>
          {couponTypes.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => onCouponTypeChange(type)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                couponType === type ? "bg-argos-400 text-white" : "text-argos-600 hover:text-argos-800"
              }`}
            >
              {TREASURY_COUPON_TYPE_LABELS[type] ?? type}
            </button>
          ))}
        </div>
      )}

      {!series || !hasAnyPoint ? (
        <EmptyState
          title="Ainda não há curva coletada"
          description={`Rode a coleta diária para popular ${TREASURY_LABELS[asset]}.`}
        />
      ) : (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
              <XAxis
                type="number"
                dataKey="x"
                domain={["dataMin", "dataMax"]}
                tickFormatter={formatYearsToMaturity}
                tick={{ fontSize: 12, fill: "#005D47" }}
                label={{ value: "Prazo até o vencimento", position: "insideBottom", offset: -4, fontSize: 11, fill: "#005D47" }}
              />
              <YAxis
                dataKey="y"
                tick={{ fontSize: 12, fill: "#005D47" }}
                tickFormatter={(v) => `${v}%`}
                width={56}
                domain={["auto", "auto"]}
              />
              <Tooltip content={<TreasuryTooltip />} />
              <Legend
                onClick={(entry) => toggleWindow(entry.dataKey as CurveWindowLabel)}
                wrapperStyle={{ cursor: "pointer", fontSize: 12 }}
              />
              {CURVE_WINDOWS.map((window) => (
                <Line
                  key={window}
                  data={series[window]}
                  type="monotone"
                  dataKey="y"
                  name={CURVE_WINDOW_LABELS[window]}
                  stroke={WINDOW_COLORS[window]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  hide={hiddenWindows.has(window)}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

type TreasurySeriesPoint = TreasuryCurvePoint & { x: number; y: number };

function TreasuryTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; color: string; name: string; payload: TreasurySeriesPoint }>;
}) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="rounded-lg border border-argos-100 bg-white p-3 text-xs shadow-md">
      {payload.map((entry) => {
        const point = entry.payload;
        return (
          <div key={`${entry.name}-${point.symbol}`} className="mb-1 last:mb-0" style={{ color: entry.color }}>
            <p className="font-medium">
              {entry.name} · {point.bond_type}
              {point.coupon_type ? ` (${TREASURY_COUPON_TYPE_LABELS[point.coupon_type] ?? point.coupon_type})` : ""}
            </p>
            <p className="text-argos-600">
              Vencimento {formatDate(point.expiration_date)} · prazo {point.time_to_maturity_years.toFixed(2)}a
            </p>
            <p className="text-argos-600">
              Compra: {point.buy_rate?.toFixed(2)}%
              {point.sell_rate !== null && point.sell_rate !== undefined ? ` · Venda: ${point.sell_rate.toFixed(2)}%` : ""}
              {" · "}
              {formatDate(point.reference_date)}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function bondOptionsFromCurve(curveView: TreasuryCurveViewResponse | null): TreasuryBondOption[] {
  if (!curveView) return [];
  const bySymbol = new Map<string, TreasuryBondOption>();
  for (const point of curveView.curves.today ?? []) {
    if (bySymbol.has(point.symbol)) continue;
    const year = new Date(`${point.expiration_date}T00:00:00Z`).getUTCFullYear();
    const label = `${point.bond_type ?? curveView.asset} ${year}`;
    bySymbol.set(point.symbol, {
      symbol: point.symbol,
      label,
      couponType: point.coupon_type,
      expirationDate: point.expiration_date,
    });
  }
  return Array.from(bySymbol.values()).sort((a, b) => a.expirationDate.localeCompare(b.expirationDate));
}

function TreasuryBondHistoryChart({ asset }: { asset: TreasuryAsset }) {
  const [curveView, setCurveView] = useState<TreasuryCurveViewResponse | null>(null);
  const [bondsLoading, setBondsLoading] = useState(true);
  const [symbol, setSymbol] = useState<string | null>(null);
  const [period, setPeriod] = useState<TreasuryBondHistoryPeriod>("90d");

  useEffect(() => {
    let cancelled = false;
    fetchJson<TreasuryCurveViewResponse>(`/api/market/treasury/${asset}/curve`)
      .then((data) => {
        if (cancelled) return;
        setCurveView(data);
        const options = bondOptionsFromCurve(data);
        setSymbol(options[0]?.symbol ?? null);
      })
      .catch(() => {
        if (!cancelled) {
          setCurveView(null);
          setSymbol(null);
        }
      })
      .finally(() => {
        if (!cancelled) setBondsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [asset]);

  const bondOptions = useMemo(() => bondOptionsFromCurve(curveView), [curveView]);

  if (bondsLoading) {
    return <div className="h-80 animate-pulse rounded-xl bg-argos-50" />;
  }

  if (!symbol || bondOptions.length === 0) {
    return (
      <EmptyState
        title="Ainda não há títulos coletados"
        description={`Rode a coleta diária para popular ${TREASURY_LABELS[asset]}.`}
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <select
        value={symbol}
        onChange={(event) => setSymbol(event.target.value)}
        className="self-start rounded-full border border-argos-100 bg-argos-50 px-3 py-1 text-xs font-medium text-argos-800"
      >
        {bondOptions.map((option) => (
          <option key={option.symbol} value={option.symbol}>
            {option.label}
          </option>
        ))}
      </select>

      {/* key remounts the body on bond/period change, resetting loading/data via initial state. */}
      <TreasuryBondHistoryBody key={`${symbol}-${period}`} symbol={symbol} period={period} onPeriodChange={setPeriod} />
    </div>
  );
}

function TreasuryBondHistoryBody({
  symbol,
  period,
  onPeriodChange,
}: {
  symbol: string;
  period: TreasuryBondHistoryPeriod;
  onPeriodChange: (period: TreasuryBondHistoryPeriod) => void;
}) {
  const [history, setHistory] = useState<TreasuryBondHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchJson<TreasuryBondHistoryResponse>(`/api/market/treasury/${symbol}/history?period=${period}`)
      .then((data) => {
        if (!cancelled) setHistory(data);
      })
      .catch(() => {
        if (!cancelled) setHistory(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, period]);

  if (loading) {
    return <div className="h-80 animate-pulse rounded-xl bg-argos-50" />;
  }

  const chartData = (history?.points ?? []).map((point) => ({
    date: formatShortDate(point.reference_date),
    reference_date: point.reference_date,
    buy_rate: point.buy_rate,
    sell_rate: point.sell_rate,
    buy_price: point.buy_price,
  }));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-argos-950">
            {history?.bond_type ?? symbol}
            {history?.coupon_type ? ` · ${TREASURY_COUPON_TYPE_LABELS[history.coupon_type] ?? history.coupon_type}` : ""}
          </p>
          <p className="text-xs text-argos-600">
            Vencimento {formatDate(history?.expiration_date ?? null)} · Taxa atual:{" "}
            <span className="font-medium text-argos-950">
              {history?.current_buy_rate !== null && history?.current_buy_rate !== undefined
                ? `${history.current_buy_rate.toFixed(2)}%`
                : "—"}
            </span>
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-argos-600">
            <span>1D: {formatBps(history?.variation_bps["1d"] ?? null)}</span>
            <span>7D: {formatBps(history?.variation_bps["7d"] ?? null)}</span>
            <span>30D: {formatBps(history?.variation_bps["30d"] ?? null)}</span>
            <span>90D: {formatBps(history?.variation_bps["90d"] ?? null)}</span>
          </div>
        </div>
        <div className="flex gap-1 rounded-full bg-argos-50 p-1">
          {TREASURY_BOND_HISTORY_PERIODS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onPeriodChange(option)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                period === option ? "bg-argos-400 text-white" : "text-argos-600 hover:text-argos-800"
              }`}
            >
              {TREASURY_BOND_HISTORY_PERIOD_LABELS[option]}
            </button>
          ))}
        </div>
      </div>

      {chartData.length === 0 ? (
        <EmptyState
          title="Ainda não há histórico suficiente"
          description="Rode o backfill para este título para ver o histórico."
        />
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#005D47" }} />
              <YAxis tick={{ fontSize: 12, fill: "#005D47" }} tickFormatter={(v) => `${v}%`} width={56} domain={["auto", "auto"]} />
              <Tooltip content={<TreasuryBondHistoryTooltip />} />
              <Line
                type="monotone"
                dataKey="buy_rate"
                stroke="#00C796"
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function TreasuryBondHistoryTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { reference_date: string; buy_rate: number | null; sell_rate: number | null; buy_price: number | null } }>;
}) {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0].payload;

  return (
    <div className="rounded-lg border border-argos-100 bg-white p-3 text-xs shadow-md">
      <p className="mb-1 font-medium text-argos-950">{formatDate(point.reference_date)}</p>
      <p className="text-argos-600">
        Compra: {point.buy_rate !== null ? `${point.buy_rate.toFixed(2)}%` : "—"}
        {point.sell_rate !== null && point.sell_rate !== undefined ? ` · Venda: ${point.sell_rate.toFixed(2)}%` : ""}
      </p>
      {point.buy_price !== null && point.buy_price !== undefined && (
        <p className="text-argos-600">Preço: {point.buy_price.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
      )}
    </div>
  );
}
