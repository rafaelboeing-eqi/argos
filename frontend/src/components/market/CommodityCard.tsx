import type { CommodityCard as CommodityCardData } from "@/types/market";
import { formatChangePct, formatDate } from "@/lib/format";

function ChangeBadge({ label, value }: { label: string; value: number | null }) {
  const color = value === null ? "text-argos-500" : value > 0 ? "text-argos-500" : value < 0 ? "text-rose-600" : "text-argos-500";
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="text-[11px] uppercase tracking-wide text-argos-500">{label}</span>
      <span className={`text-sm font-medium ${color}`}>{formatChangePct(value)}</span>
    </div>
  );
}

export function CommodityCard({
  commodity,
  onClick,
}: {
  commodity: CommodityCardData;
  onClick: () => void;
}) {
  const hasValue = commodity.value !== null;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!hasValue}
      className="flex flex-col gap-3 rounded-2xl bg-white p-5 text-left shadow-sm ring-1 ring-argos-100 transition hover:ring-argos-400 disabled:cursor-not-allowed disabled:opacity-70"
    >
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-argos-800">{commodity.label}</span>
        {commodity.symbol && <span className="text-xs text-argos-500">{commodity.symbol}</span>}
      </div>

      {hasValue ? (
        <>
          <span className="text-2xl font-semibold text-argos-950">
            {commodity.value?.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <div className="flex justify-between gap-2 border-t border-argos-100 pt-3">
            <ChangeBadge label="1d" value={commodity.change_1d} />
            <ChangeBadge label="7d" value={commodity.change_7d} />
            <ChangeBadge label="30d" value={commodity.change_30d} />
          </div>
          <span className="text-xs text-argos-500">{formatDate(commodity.reference_date)}</span>
        </>
      ) : (
        <span className="text-sm text-argos-500">Sem dados ainda</span>
      )}
    </button>
  );
}
