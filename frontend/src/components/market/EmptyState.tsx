export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-argos-200 bg-white/60 px-6 py-12 text-center">
      <p className="text-sm font-medium text-argos-800">{title}</p>
      <p className="max-w-sm text-sm text-argos-600">{description}</p>
    </div>
  );
}
