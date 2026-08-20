export function MetricCard({
  label,
  value,
  caption,
  muted,
}: {
  label: string;
  value: string;
  caption?: string;
  muted?: boolean;
}) {
  return (
    <div className={`flex flex-col gap-1 rounded-xl border border-argos-100 bg-white p-4 ${muted ? "opacity-60" : ""}`}>
      <span className="text-xs font-medium uppercase tracking-wide text-argos-500">{label}</span>
      <span className="text-2xl font-semibold text-argos-950">{value}</span>
      {caption && <span className="text-xs text-argos-500">{caption}</span>}
    </div>
  );
}
