import type { ActivityStatus } from "@/lib/types/api";

const LABELS: Record<ActivityStatus, string> = {
  active: "Aktiv",
  idle: "Inaktiv",
  never: "Noch nie",
};

const STYLES: Record<ActivityStatus, string> = {
  active: "bg-okbg text-oktext",
  idle: "bg-warnbg text-warntext",
  never: "bg-surface2 text-muted",
};

export function ActivityBadge({ status }: { status: ActivityStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
