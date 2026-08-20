import type { TrackedFlag } from "@/types/credit";
import { EmptyState } from "@/components/ui/EmptyState";

const STATUS_STYLE: Record<string, string> = {
  aberto: "bg-amber-100 text-amber-800",
  confirmado: "bg-red-100 text-red-800",
  revertido: "bg-argos-100 text-argos-800",
  resolvido: "bg-argos-100 text-argos-800",
};

const CATEGORIA_LABEL: Record<TrackedFlag["categoria"], string> = {
  red_flag: "Red flag",
  ponto_atencao: "Ponto de atenção",
};

export function TrackedFlagsList({ flags }: { flags: TrackedFlag[] }) {
  if (flags.length === 0) {
    return <EmptyState title="Nenhum flag rastreado" description="Flags aparecem aqui depois da primeira análise do Master Agent." />;
  }

  return (
    <ul className="flex flex-col gap-3">
      {flags.map((flag) => (
        <li key={flag.id} className="flex flex-col gap-1 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-argos-100">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-argos-500">
              {CATEGORIA_LABEL[flag.categoria]}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[flag.status] ?? "bg-argos-100 text-argos-800"}`}>
              {flag.status}
            </span>
          </div>
          <p className="text-sm text-argos-950">{flag.descricao}</p>
        </li>
      ))}
    </ul>
  );
}
