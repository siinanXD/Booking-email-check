/** Shared formatting helpers (previously duplicated across admin pages). */

export function formatUsd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "$0.00";
  return `$${value.toFixed(2)}`;
}

export function formatTs(
  value: string | number | Date | null | undefined,
  locale = "de-DE"
): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(locale);
}
