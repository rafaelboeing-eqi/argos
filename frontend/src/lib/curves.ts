import { CURVE_WINDOWS, type CurveWindowLabel } from "@/types/market";

/**
 * Reshapes the backend's {today: [...], "7d": [...], ...} curve windows into
 * one row per X-axis key, each row carrying whichever windows have a value
 * for that key - exactly what a multi-line Recharts chart needs. Purely a
 * chart-data-shaping helper (no rates/thresholds computed here).
 */
export function mergeCurveWindows<T>(
  curves: Record<CurveWindowLabel, T[]>,
  keyFn: (point: T) => string,
  valueFn: (point: T) => number | null | undefined
): Array<{ key: string } & Partial<Record<CurveWindowLabel, number>>> {
  const rowsByKey = new Map<string, { key: string } & Partial<Record<CurveWindowLabel, number>>>();

  for (const window of CURVE_WINDOWS) {
    for (const point of curves[window] ?? []) {
      const value = valueFn(point);
      if (value === null || value === undefined) continue;
      const key = keyFn(point);
      const row = rowsByKey.get(key) ?? { key };
      row[window] = value;
      rowsByKey.set(key, row);
    }
  }

  return Array.from(rowsByKey.values()).sort((a, b) => a.key.localeCompare(b.key));
}
