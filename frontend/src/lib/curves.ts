import { CURVE_WINDOWS, type CurveWindowLabel } from "@/types/market";

/**
 * Turns the backend's {today: [...], "7d": [...], ...} curve windows into one
 * sorted-by-x array per window, ready for a <Line data={...}> with its own
 * independent series. Each window's snapshot sits at its own (slightly
 * different) time-to-maturity - the "today" point for a contract expiring in
 * exactly a year sits at x=1.0, while the "90d" snapshot of that SAME contract
 * sits a bit farther out, since its reference_date is 90 days earlier and the
 * expiration_date never moves. That's why windows can no longer share one
 * merged row per X value the way calendar-year categories used to.
 */
export function buildCurveSeries<T>(
  curves: Record<CurveWindowLabel, T[]>,
  xFn: (point: T) => number,
  yFn: (point: T) => number | null | undefined
): Record<CurveWindowLabel, Array<T & { x: number; y: number }>> {
  const result = {} as Record<CurveWindowLabel, Array<T & { x: number; y: number }>>;
  for (const window of CURVE_WINDOWS) {
    result[window] = (curves[window] ?? [])
      .reduce<Array<T & { x: number; y: number }>>((acc, point) => {
        const y = yFn(point);
        if (y === null || y === undefined) return acc;
        acc.push({ ...point, x: xFn(point), y });
        return acc;
      }, [])
      .sort((a, b) => a.x - b.x);
  }
  return result;
}
