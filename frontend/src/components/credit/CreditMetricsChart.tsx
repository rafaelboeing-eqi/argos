"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { CreditMetric } from "@/types/credit";
import { EmptyState } from "@/components/ui/EmptyState";

const SERIES = [
  { key: "margem_ebitda", label: "Margem EBITDA", color: "#00C796" },
  { key: "divida_liquida_ebitda", label: "Dívida líquida / EBITDA", color: "#005D47" },
] as const;

export function CreditMetricsChart({ metrics }: { metrics: CreditMetric[] }) {
  const hasAnyRatio = metrics.some((m) => m.margem_ebitda !== null || m.divida_liquida_ebitda !== null);

  if (!hasAnyRatio) {
    return (
      <EmptyState
        title="Sem indicadores calculáveis ainda"
        description="Ingira demonstrativos com receita_liquida, ebitda e divida_liquida para ver a evolução aqui."
      />
    );
  }

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={metrics} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#DFEEEB" />
          <XAxis dataKey="period" tick={{ fontSize: 12, fill: "#005D47" }} />
          <YAxis
            yAxisId="pct"
            tick={{ fontSize: 12, fill: "#005D47" }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            width={48}
          />
          <YAxis
            yAxisId="mult"
            orientation="right"
            tick={{ fontSize: 12, fill: "#005D47" }}
            tickFormatter={(v: number) => `${v.toFixed(1)}x`}
            width={40}
          />
          <Tooltip
            formatter={(value, name) => {
              const num = Number(value);
              return name === "Margem EBITDA" ? [`${(num * 100).toFixed(1)}%`, name] : [`${num.toFixed(1)}x`, name];
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="margem_ebitda"
            name={SERIES[0].label}
            stroke={SERIES[0].color}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="mult"
            type="monotone"
            dataKey="divida_liquida_ebitda"
            name={SERIES[1].label}
            stroke={SERIES[1].color}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
