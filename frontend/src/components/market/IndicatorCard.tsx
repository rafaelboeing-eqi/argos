import type { IndicatorCard as IndicatorCardData } from "@/types/market";
import { formatDate, formatPercent } from "@/lib/format";

export function IndicatorCard({ indicator }: { indicator: IndicatorCardData }) {
  const hasValue = indicator.value !== null;

  return (
    <div className="flex flex-col gap-2 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-argos-100">
      <span className="text-xs font-medium uppercase tracking-wide text-argos-500">{indicator.label}</span>
      {hasValue ? (
        <>
          <span className="text-2xl font-semibold text-argos-950">{formatPercent(indicator.value)}</span>
          <span className="text-xs text-argos-500">{formatDate(indicator.reference_date)}</span>
        </>
      ) : (
        <span className="text-sm text-argos-500">Sem dados ainda</span>
      )}
    </div>
  );
}
