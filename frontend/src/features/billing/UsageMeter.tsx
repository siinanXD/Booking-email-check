import {
  formatLimit,
  UNLIMITED,
  usageBarTone,
  usagePercent,
  usageTextTone,
} from "@/lib/billing/display";

export function UsageMeter({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  const pct = usagePercent(used, limit);
  const unlimited = limit === UNLIMITED;

  return (
    <div>
      <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5 text-xs">
        <span className="font-medium text-muted">{label}</span>
        <span
          className={`font-numeric ${unlimited ? "text-ink2" : usageTextTone(pct)}`}
        >
          {used.toLocaleString("de-DE")} / {formatLimit(limit)}
        </span>
      </div>
      {!unlimited && (
        <div
          className="h-2 overflow-hidden rounded-full bg-surface2"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label}: ${pct} Prozent`}
        >
          <div
            className={`h-full rounded-full transition-all duration-300 ${usageBarTone(pct)}`}
            style={{ width: `${Math.max(pct, pct > 0 ? 4 : 0)}%` }}
          />
        </div>
      )}
    </div>
  );
}
