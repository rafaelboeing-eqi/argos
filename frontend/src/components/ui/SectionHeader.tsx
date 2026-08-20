import type { ReactNode } from "react";

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-argos-600">{title}</h2>
      {action}
    </div>
  );
}
