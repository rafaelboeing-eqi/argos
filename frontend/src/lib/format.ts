export function formatPercent(value: number | null, digits = 2): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}%`;
}

export function formatChangePct(value: number | null): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00Z`);
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC" });
}

export function formatShortDate(value: string): string {
  const date = new Date(`${value}T00:00:00Z`);
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", timeZone: "UTC" });
}

export function formatYearsToMaturity(value: number): string {
  return `${value.toFixed(1)}a`;
}

export function formatBps(value: number | null): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(0)} bps`;
}

export function formatRatioAsPercent(value: number | null, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return formatPercent(value * 100, digits);
}

export function formatMultiple(value: number | null, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}x`;
}

export function formatCurrencyCompact(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const iso = value.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}
