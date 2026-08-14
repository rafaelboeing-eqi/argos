import { formatDate } from "@/lib/format";

/**
 * Argos never calls brapi while a user is on this page - every number here comes
 * from Postgres. This badge is what keeps that honest: it always shows the date
 * of the newest data actually stored, so the page stays truthful even if the
 * ingestion job has been failing against brapi for a few days.
 */
export function DataFreshnessBadge({ dataAsOf }: { dataAsOf: string | null }) {
  if (!dataAsOf) {
    return <span className="text-xs text-argos-500">Ainda sem dados coletados</span>;
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-argos-50 px-3 py-1 text-xs font-medium text-argos-600">
      <span className="h-1.5 w-1.5 rounded-full bg-argos-400" />
      Dados atualizados até {formatDate(dataAsOf)}
    </span>
  );
}
