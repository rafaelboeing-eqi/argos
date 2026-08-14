"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "@/lib/api";
import { formatShortDate } from "@/lib/format";
import type { HistoryResponse } from "@/types/market";
import { EmptyState } from "./EmptyState";

export function CommodityHistoryPanel({
  symbol,
  label,
  onClose,
}: {
  symbol: string;
  label: string;
  onClose: () => void;
}) {
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchJson<HistoryResponse>(`/api/market/futures/${symbol}/history`)
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
  }, [symbol]);

  const chartData = (history?.points ?? []).map((point) => ({
    date: formatShortDate(point.reference_date),
    value: point.value,
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-argos-950/40 p-4" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl" onClick={(event) => event.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-argos-950">{label}</h3>
            <p className="text-xs text-argos-500">{symbol}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="rounded-full px-2 py-1 text-sm text-argos-500 hover:bg-argos-50"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="h-64 animate-pulse rounded-xl bg-argos-50" />
        ) : chartData.length === 0 ? (
          <EmptyState
            title="Sem histórico ainda"
            description="Rode o backfill para este contrato para ver o gráfico histórico."
          />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#005D47" }} />
                <YAxis tick={{ fontSize: 12, fill: "#005D47" }} width={56} />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#00C796" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
