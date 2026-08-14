"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { formatShortDate } from "@/lib/format";
import type { CurveResponse } from "@/types/market";
import { EmptyState } from "./EmptyState";

const CURVE_ASSETS = [
  { key: "DI1", label: "DI" },
  { key: "DAP", label: "DAP" },
] as const;

type CurveAssetKey = (typeof CURVE_ASSETS)[number]["key"];

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
      <CurveChartBody key={asset} asset={asset} />
    </section>
  );
}

function CurveChartBody({ asset }: { asset: CurveAssetKey }) {
  const [curve, setCurve] = useState<CurveResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchJson<CurveResponse>(`/api/market/futures/${asset}/curve`)
      .then((data) => {
        if (!cancelled) setCurve(data);
      })
      .catch(() => {
        if (!cancelled) setCurve(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [asset]);

  const chartData = (curve?.points ?? []).map((point) => ({
    expiration: point.expiration_date ? formatShortDate(point.expiration_date) : point.symbol,
    value: point.value,
  }));

  if (loading) {
    return <div className="h-72 animate-pulse rounded-xl bg-argos-50" />;
  }

  if (chartData.length === 0) {
    return (
      <EmptyState
        title="Ainda não há curva coletada"
        description={`Rode a coleta diária para popular a curva de ${asset}.`}
      />
    );
  }

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
          <XAxis dataKey="expiration" tick={{ fontSize: 12, fill: "#005D47" }} />
          <YAxis tick={{ fontSize: 12, fill: "#005D47" }} tickFormatter={(v) => `${v}%`} width={56} />
          <Tooltip
            formatter={(value) => [`${Number(value).toFixed(3)}%`, "Taxa"]}
            labelFormatter={(label) => `Vencimento ${label}`}
          />
          <Line type="monotone" dataKey="value" stroke="#00C796" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
