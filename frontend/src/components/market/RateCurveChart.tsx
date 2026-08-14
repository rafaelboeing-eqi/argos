"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { mergeCurveWindows } from "@/lib/curves";
import { formatDate } from "@/lib/format";
import { CURVE_WINDOW_LABELS, CURVE_WINDOWS, type CurveWindowLabel, type RateCurveViewResponse } from "@/types/market";
import { EmptyState } from "./EmptyState";

const CURVE_ASSETS = [
  { key: "DI1", label: "DI" },
  { key: "DAP", label: "DAP" },
] as const;

type CurveAssetKey = (typeof CURVE_ASSETS)[number]["key"];

const WINDOW_COLORS: Record<CurveWindowLabel, string> = {
  today: "#00C796",
  "7d": "#009E76",
  "30d": "#005D47",
  "90d": "#A8D5C6",
};

export function RateCurveChart() {
  const [asset, setAsset] = useState<CurveAssetKey>("DI1");

  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-argos-100">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-argos-950">Curva de Juros</h2>
        <div className="flex gap-1 rounded-full bg-argos-50 p-1">
          {CURVE_ASSETS.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setAsset(option.key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                asset === option.key ? "bg-argos-400 text-white" : "text-argos-600 hover:text-argos-800"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* key={asset} remounts this on toggle, so loading/curve reset via their
          initial state instead of an extra setState call inside the effect. */}
      <RateCurveChartBody key={asset} asset={asset} />
    </section>
  );
}

function RateCurveChartBody({ asset }: { asset: CurveAssetKey }) {
  const [curveView, setCurveView] = useState<RateCurveViewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [hiddenWindows, setHiddenWindows] = useState<Set<CurveWindowLabel>>(new Set());

  useEffect(() => {
    let cancelled = false;
    fetchJson<RateCurveViewResponse>(`/api/market/futures/${asset}/rate-curve`)
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
  }, [asset]);

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
  const chartData = curves
    ? mergeCurveWindows(
        curves,
        (point) => String(new Date(`${point.expiration_date}T00:00:00Z`).getUTCFullYear()),
        (point) => point.value
      )
    : [];

  if (chartData.length === 0) {
    return (
      <EmptyState
        title="Ainda não há curva coletada"
        description={`Rode a coleta diária para popular a curva de ${asset}.`}
      />
    );
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
          <XAxis dataKey="key" tick={{ fontSize: 12, fill: "#005D47" }} />
          <YAxis tick={{ fontSize: 12, fill: "#005D47" }} tickFormatter={(v) => `${v}%`} width={56} />
          <Tooltip content={<RateCurveTooltip curves={curves} />} />
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
  );
}

function RateCurveTooltip({
  active,
  payload,
  label,
  curves,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: CurveWindowLabel; value: number; color: string }>;
  label?: string;
  curves?: RateCurveViewResponse["curves"];
}) {
  if (!active || !payload || !payload.length || !curves) return null;

  return (
    <div className="rounded-lg border border-argos-100 bg-white p-3 text-xs shadow-md">
      <p className="mb-1 font-medium text-argos-950">Vencimento {label}</p>
      {payload.map((entry) => {
        const point = curves[entry.dataKey]?.find(
          (p) => String(new Date(`${p.expiration_date}T00:00:00Z`).getUTCFullYear()) === label
        );
        return (
          <div key={entry.dataKey} className="flex items-center justify-between gap-4" style={{ color: entry.color }}>
            <span>
              {CURVE_WINDOW_LABELS[entry.dataKey]}
              {point ? ` (${point.symbol})` : ""}
            </span>
            <span className="font-medium">
              {entry.value.toFixed(3)}% {point ? `· ${formatDate(point.reference_date)}` : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}
