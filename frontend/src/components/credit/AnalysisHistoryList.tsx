import type { AnalysisRecord } from "@/types/credit";
import { formatDateTime } from "@/lib/format";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";

const RISCO_TONE: Record<AnalysisRecord["risco_credito"]["nivel"], "positivo" | "observacao" | "atencao" | "critico"> = {
  baixo: "positivo",
  moderado: "observacao",
  elevado: "atencao",
  critico: "critico",
};

export function AnalysisHistoryList({ analyses }: { analyses: AnalysisRecord[] }) {
  if (analyses.length === 0) {
    return (
      <EmptyState
        title="Nenhuma análise rodada ainda"
        description="Rode a primeira análise na aba Análises para começar o histórico desta empresa."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {analyses.map((analysis) => (
        <li key={analysis.id} className="flex flex-col gap-2 rounded-xl border border-argos-100 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-argos-500">
              {analysis.period ?? "Sem período"} · {formatDateTime(analysis.created_at)}
            </span>
            <StatusBadge tone={RISCO_TONE[analysis.risco_credito.nivel]}>
              {analysis.risco_credito.nivel} · {analysis.tendencia}
            </StatusBadge>
          </div>
          <p className="text-sm text-argos-950">{analysis.output.resumo_executivo}</p>
        </li>
      ))}
    </ul>
  );
}
