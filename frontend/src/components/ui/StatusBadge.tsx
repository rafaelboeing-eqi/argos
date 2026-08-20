import type { ReactNode } from "react";

export type StatusTone = "critico" | "atencao" | "observacao" | "positivo" | "neutro";

export const TONE_BADGE_STYLE: Record<StatusTone, string> = {
  critico: "bg-red-100 text-red-700",
  atencao: "bg-orange-100 text-orange-700",
  observacao: "bg-amber-100 text-amber-800",
  positivo: "bg-argos-100 text-argos-800",
  neutro: "bg-zinc-100 text-zinc-600",
};

export const TONE_DOT_STYLE: Record<StatusTone, string> = {
  critico: "bg-red-500",
  atencao: "bg-orange-500",
  observacao: "bg-amber-500",
  positivo: "bg-argos-400",
  neutro: "bg-zinc-400",
};

export function StatusBadge({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE_BADGE_STYLE[tone]}`}>
      {children}
    </span>
  );
}
