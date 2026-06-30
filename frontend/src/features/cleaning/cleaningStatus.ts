/** Mapping der Putzauftrag-Status auf Badge-Töne. */
export const STATUS_TONE: Record<string, string> = {
  unassigned: "pending",
  scheduled: "booking",
  notified: "inquiry",
  done: "approved",
  cancelled: "rejected",
};

/** Auswahloptionen für den Status-Filter. */
export const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Alle Status" },
  { value: "unassigned", label: "Offen (kein Partner)" },
  { value: "scheduled", label: "Geplant" },
  { value: "notified", label: "Benachrichtigt" },
  { value: "done", label: "Erledigt" },
  { value: "cancelled", label: "Storniert" },
];

export function toneFor(status: string): string {
  return STATUS_TONE[status] ?? "default";
}
