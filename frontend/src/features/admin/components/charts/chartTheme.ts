/** Einheitliche Farben für Admin-Diagramme (Design-Tokens als CSS-Variablen). */
export const ADMIN_CHART = {
  indigo: "var(--brand)",
  emerald: "var(--oktext)",
  amber: "var(--warntext)",
  slate: "var(--muted)",
  rose: "var(--dangertext)",
  violet: "var(--brand2)",
} as const;

export const ACTIVITY_COLORS: Record<string, string> = {
  active: ADMIN_CHART.emerald,
  idle: ADMIN_CHART.amber,
  never: ADMIN_CHART.slate,
};

export const ACTIVITY_LABELS: Record<string, string> = {
  active: "Aktiv (7 Tage)",
  idle: "Inaktiv",
  never: "Noch nie",
};

export const STATUS_COLORS: Record<string, string> = {
  active: ADMIN_CHART.emerald,
  pending: ADMIN_CHART.amber,
  rejected: ADMIN_CHART.rose,
  suspended: ADMIN_CHART.slate,
};

export const STATUS_LABELS: Record<string, string> = {
  active: "Freigeschaltet",
  pending: "Ausstehend",
  rejected: "Abgelehnt",
  suspended: "Gesperrt",
};
