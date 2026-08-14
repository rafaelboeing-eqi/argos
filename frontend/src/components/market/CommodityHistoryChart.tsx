"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { formatChangePct, formatShortDate } from "@/lib/format";
import {
  COMMODITY_ASSETS,
  COMMODITY_HISTORY_PERIODS,
  COMMODITY_HISTORY_PERIOD_LABELS,
  type CommodityAsset,
  type CommodityCard,
  type CommodityHistoryApiResponse,
  type CommodityHistoryPeriod,
} from "@/types/market";
import { EmptyState } from "./EmptyState";

const Y_DOMAIN_PADDING_RATIO = 0.04;

/**
 * A commodity's price rarely swings anywhere near zero, so a Y axis pinned at 0
 * flattens the very oscillations the chart exists to show (e.g. BGI moving
 * between 330-358 looks like a flat line against a 0-360 axis). Zoom to the
 * window's own min/max with a small padding instead - never changes the
 * underlying values, only how the same values are framed.
 */
function computeYDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const pad = Math.abs(min) * Y_DOMAIN_PADDING_RATIO || 1;
    return [min - pad, max + pad];
  }
  const pad = (max - min) * Y_DOMAIN_PADDING_RATIO;
  return [min - pad, max + pad];
}

export function CommodityHistoryChart({ commodities }: { commodities: CommodityCard[] }) {
  const [asset, setAsset] = useState<CommodityAsset>("BGI");
  const [period, setPeriod] = useState<CommodityHistoryPeriod>("90d");

  const selected = commodities.find((commodity) => commodity.asset === asset) ?? null;

  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-argos-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-argos-950">Histórico de Commodities</h2>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={asset}
            onChange={(event) => setAsset(event.target.value as CommodityAsset)}
            className="rounded-full border border-argos-100 bg-argos-50 px-3 py-1 text-xs font-medium text-argos-800"
          >
            {COMMODITY_ASSETS.map((option) => (
              <option key={option} value={option}>
                {commodities.find((c) => c.asset === option)?.label ?? option}
              </option>
            ))}
          </select>
          <div className="flex gap-1 rounded-full bg-argos-50 p-1">
            {COMMODITY_HISTORY_PERIODS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setPeriod(option)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  period === option ? "bg-argos-400 text-white" : "text-argos-600 hover:text-argos-800"
                }`}
              >
                {COMMODITY_HISTORY_PERIOD_LABELS[option]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {selected && (
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-argos-600">
          <span>
            Série: <span className="font-medium text-argos-950">{selected.symbol ?? "—"}</span>
          </span>
          <span>
            Valor: <span className="font-medium text-argos-950">{selected.value?.toFixed(2) ?? "—"}</span>
          </span>
          <span>1D: {formatChangePct(selected.change_1d)}</span>
          <span>7D: {formatChangePct(selected.change_7d)}</span>
          <span>30D: {formatChangePct(selected.change_30d)}</span>
          {selected.change_90d !== null && <span>90D: {formatChangePct(selected.change_90d)}</span>}
        </div>
      )}

      {/* key remounts the body on asset/period change, resetting loading/data via initial state. */}
      <CommodityHistoryChartBody key={`${asset}-${period}`} asset={asset} period={period} />
    </section>
  );
}

function CommodityHistoryChartBody({ asset, period }: { asset: CommodityAsset; period: CommodityHistoryPeriod }) {
  const [history, setHistory] = useState<CommodityHistoryApiResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchJson<CommodityHistoryApiResponse>(`/api/market/commodities/${asset}/history?period=${period}`)
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
  }, [asset, period]);

  if (loading) {
    return <div className="h-64 animate-pulse rounded-xl bg-argos-50" />;
  }

  const chartData = (history?.points ?? []).map((point) => ({
    date: formatShortDate(point.reference_date),
    value: point.value,
  }));

  if (chartData.length === 0) {
    return (
      <EmptyState
        title="Ainda não há histórico suficiente"
        description="Rode o backfill para este contrato para ver o gráfico histórico."
      />
    );
  }

  const yDomain = computeYDomain(chartData.map((point) => point.value));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#005D47" }} />
          <YAxis
            tick={{ fontSize: 12, fill: "#005D47" }}
            tickFormatter={(v: number) => v.toFixed(1)}
            width={64}
            domain={yDomain}
            allowDataOverflow
          />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#00C796" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
