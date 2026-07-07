/** Shared billing display helpers (plans, limits, usage). */

export const UNLIMITED = -1;

export function formatLimit(value: number): string {
  return value === UNLIMITED ? "∞" : value.toLocaleString("de-DE");
}

export function usagePercent(used: number, limit: number): number {
  if (limit <= 0 || limit === UNLIMITED) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

export function usageBarTone(percent: number): string {
  if (percent >= 100) return "bg-dangertext";
  if (percent >= 80) return "bg-warntext";
  return "bg-brand";
}

export function usageTextTone(percent: number): string {
  if (percent >= 100) return "text-dangertext";
  if (percent >= 80) return "text-warntext";
  return "text-ink2";
}

const STATUS_LABELS: Record<string, string> = {
  trialing: "Trial",
  active: "Aktiv",
  past_due: "Zahlung ausstehend",
  canceled: "Beendet",
};

export function subscriptionStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export const BILLING_SETTINGS_HASH = "abo-verbrauch";

export const BILLING_SETTINGS_PATH = `/settings#${BILLING_SETTINGS_HASH}`;
