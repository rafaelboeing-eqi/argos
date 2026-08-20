import { TONE_DOT_STYLE, type StatusTone } from "./StatusBadge";

export function AlertCard({
  tone,
  title,
  description,
  timestamp,
}: {
  tone: StatusTone;
  title: string;
  description: string;
  timestamp?: string;
}) {
  return (
    <div className="flex gap-3 border-b border-argos-50 py-3 last:border-0">
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${TONE_DOT_STYLE[tone]}`} />
      <div className="flex flex-col gap-0.5">
        <p className="text-sm font-medium text-argos-950">{title}</p>
        <p className="text-xs text-argos-600">{description}</p>
        {timestamp && <p className="text-xs text-argos-400">{timestamp}</p>}
      </div>
    </div>
  );
}
