import type { DebtMaturity } from "@/types/credit";
import { formatCurrencyCompact } from "@/lib/format";
import { EmptyState } from "@/components/ui/EmptyState";

const COVENANT_STYLE: Record<string, string> = {
  compliant: "bg-argos-100 text-argos-800",
  em_observacao: "bg-amber-100 text-amber-800",
  violado: "bg-red-100 text-red-800",
};

export function DebtScheduleTable({ debts }: { debts: DebtMaturity[] }) {
  if (debts.length === 0) {
    return <EmptyState title="Sem cronograma de dívida" description="Ingira vencimentos de dívida e covenants para ver aqui." />;
  }

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm ring-1 ring-argos-100">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-argos-100 text-xs uppercase tracking-wide text-argos-500">
            <th className="px-4 py-3">Descrição</th>
            <th className="px-4 py-3">Vencimento</th>
            <th className="px-4 py-3">Valor</th>
            <th className="px-4 py-3">Covenant</th>
          </tr>
        </thead>
        <tbody>
          {debts.map((debt) => (
            <tr key={debt.id} className="border-b border-argos-50 last:border-0">
              <td className="px-4 py-3 font-medium text-argos-950">{debt.descricao}</td>
              <td className="px-4 py-3 text-argos-600">{debt.vencimento ?? "—"}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(debt.valor)}</td>
              <td className="px-4 py-3">
                {debt.covenant_status ? (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${COVENANT_STYLE[debt.covenant_status]}`}
                  >
                    {debt.covenant_status}
                  </span>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
