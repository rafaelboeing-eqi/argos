"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { mergeCurveWindows } from "@/lib/curves";
import { formatDate, formatShortDate } from "@/lib/format";
import {
  CURVE_WINDOW_LABELS,
  CURVE_WINDOWS,
  TREASURY_ASSETS,
  TREASURY_COUPON_TYPE_LABELS,
  TREASURY_IS_REAL_RATE,
  TREASURY_LABELS,
  type CurveWindowLabel,
  type TreasuryAsset,
  type TreasuryCurveViewResponse,
} from "@/types/market";
import { EmptyState } from "./EmptyState";

const WINDOW_COLORS: Record<CurveWindowLabel, string> = {
  today: "#00C796",
  "7d": "#009E76",
  "30d": "#005D47",
  "90d": "#A8D5C6",
};

export function TreasuryCurveChart() {
  const [asset, setAsset] = useState<TreasuryAsset>("treasury_ipca");
  const [couponType, setCouponType] = useState<string | null>(null);

  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-argos-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-argos-950">Tesouro Direto</h2>
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

      {TREASURY_IS_REAL_RATE[asset] && (
        <p className="text-xs text-argos-500">Taxa real anual acima do IPCA.</p>
      )}

      {/* key remounts the body on asset change, resetting loading/data via initial state. */}
      <TreasuryCurveChartBody key={asset} asset={asset} couponType={couponType} onCouponTypeChange={setCouponType} />
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

  if (loading) {
    return <div className="h-72 animate-pulse rounded-xl bg-argos-50" />;
  }

  const curves = curveView?.curves;
  const couponTypes = curveView?.coupon_types ?? [];
  const chartData = curves ? mergeCurveWindows(curves, (point) => point.expiration_date, (point) => point.buy_rate) : [];

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

      {chartData.length === 0 ? (
        <EmptyState
          title="Ainda não há curva coletada"
          description={`Rode a coleta diária para popular ${TREASURY_LABELS[asset]}.`}
        />
      ) : (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
              <XAxis dataKey="key" tickFormatter={(value) => formatShortDate(value)} tick={{ fontSize: 12, fill: "#005D47" }} />
              <YAxis tick={{ fontSize: 12, fill: "#005D47" }} tickFormatter={(v) => `${v}%`} width={56} />
              <Tooltip content={<TreasuryTooltip curves={curves} />} />
              <Legend
                onClick={(entry) => toggleWindow(entry.dataKey as CurveWindowLabel)}
                wrapperStyle={{ cursor: "pointer", fontSize: 12 }}
              />
              {CURVE_WINDOWS.map((window) => (
                <Line
                  key={window}
                  type="monotone"
                  dataKey={window}
                  name={CURVE_WINDOW_LABELS[window]}
                  stroke={WINDOW_COLORS[window]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  hide={hiddenWindows.has(window)}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function TreasuryTooltip({
  active,
  payload,
  label,
  curves,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: CurveWindowLabel; value: number; color: string }>;
  label?: string;
  curves?: TreasuryCurveViewResponse["curves"];
}) {
  if (!active || !payload || !payload.length || !curves) return null;

  return (
    <div className="rounded-lg border border-argos-100 bg-white p-3 text-xs shadow-md">
      <p className="mb-1 font-medium text-argos-950">Vencimento {formatDate(label ?? null)}</p>
      {payload.map((entry) => {
        const point = curves[entry.dataKey]?.find((p) => p.expiration_date === label);
        if (!point) return null;
        return (
          <div key={entry.dataKey} className="mb-1 last:mb-0">
            <p style={{ color: entry.color }} className="font-medium">
              {CURVE_WINDOW_LABELS[entry.dataKey]} · {point.bond_type}
              {point.coupon_type ? ` (${TREASURY_COUPON_TYPE_LABELS[point.coupon_type] ?? point.coupon_type})` : ""}
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
