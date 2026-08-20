"use client";

import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { buildCurveSeries } from "@/lib/curves";
import { formatDate, formatYearsToMaturity } from "@/lib/format";
import {
  CURVE_WINDOW_LABELS,
  CURVE_WINDOWS,
  type CurveWindowLabel,
  type RateCurvePoint,
  type RateCurveViewResponse,
} from "@/types/market";
import { EmptyState } from "@/components/ui/EmptyState";

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

type SeriesPoint = RateCurvePoint & { x: number; y: number };

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

  const curves = curveView?.curves;
  // Memoized so the array/object identities stay stable across re-renders (e.g.
  // hover/tooltip state) - recomputing fresh objects on every render made Recharts
  // treat the data as brand new each time, restarting the line-draw animation and
  // making the curve flicker away mid-hover. Called unconditionally (before the
  // loading early-return) to satisfy the rules of hooks.
  const series = useMemo(
    () =>
      curves
        ? buildCurveSeries(
            curves,
            (point) => point.time_to_maturity_years,
            (point) => point.value
          )
        : null,
    [curves]
  );

  if (loading) {
    return <div className="h-72 animate-pulse rounded-xl bg-argos-50" />;
  }
  const hasAnyPoint = series ? CURVE_WINDOWS.some((window) => series[window].length > 0) : false;

  if (!series || !hasAnyPoint) {
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
          <Tooltip content={<RateCurveTooltip />} />
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
  );
}

function RateCurveTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; color: string; name: string; payload: SeriesPoint }>;
}) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="rounded-lg border border-argos-100 bg-white p-3 text-xs shadow-md">
      {payload.map((entry) => {
        const point = entry.payload;
        return (
          <div key={`${entry.name}-${point.symbol}`} className="mb-1 last:mb-0" style={{ color: entry.color }}>
            <p className="font-medium">
              {entry.name} · {point.symbol}
            </p>
            <p className="text-argos-600">
              Vencimento {formatDate(point.expiration_date)} · prazo {point.time_to_maturity_years.toFixed(2)}a
            </p>
            <p className="text-argos-600">
              Taxa: <span className="font-medium text-argos-950">{point.value.toFixed(3)}%</span>
              {" · "}
              {formatDate(point.reference_date)}
            </p>
          </div>
        );
      })}
    </div>
  );
}
