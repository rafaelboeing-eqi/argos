import type { FinancialStatement } from "@/types/credit";
import { formatCurrencyCompact } from "@/lib/format";
import { EmptyState } from "@/components/ui/EmptyState";

export function FinancialStatementsTable({ statements }: { statements: FinancialStatement[] }) {
  if (statements.length === 0) {
    return (
      <EmptyState
        title="Nenhum demonstrativo ingerido"
        description="Ingira um período (DRE/Balanço/Fluxo de Caixa) para ver os dados aqui."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm ring-1 ring-argos-100">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-argos-100 text-xs uppercase tracking-wide text-argos-500">
            <th className="px-4 py-3">Período</th>
            <th className="px-4 py-3">Tipo</th>
            <th className="px-4 py-3">Receita líquida</th>
            <th className="px-4 py-3">EBITDA</th>
            <th className="px-4 py-3">Lucro líquido</th>
            <th className="px-4 py-3">Dívida bruta</th>
            <th className="px-4 py-3">Dívida líquida</th>
            <th className="px-4 py-3">Caixa</th>
          </tr>
        </thead>
        <tbody>
          {statements.map((row) => (
            <tr key={row.id} className="border-b border-argos-50 last:border-0">
              <td className="px-4 py-3 font-medium text-argos-950">{row.period}</td>
              <td className="px-4 py-3 text-argos-600">{row.statement_type}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(row.receita_liquida)}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(row.ebitda)}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(row.lucro_liquido)}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(row.divida_bruta)}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(row.divida_liquida)}</td>
              <td className="px-4 py-3">{formatCurrencyCompact(row.caixa)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
