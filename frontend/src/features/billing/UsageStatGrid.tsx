import {
  formatLimit,
  usagePercent,
  usageTextTone,
} from "@/lib/billing/display";

export interface UsageStatItem {
  label: string;
  used: number;
  limit: number;
}

export function UsageStatGrid({ items }: { items: UsageStatItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <UsageStatTile key={item.label} {...item} />
      ))}
    </div>
  );
}

function UsageStatTile({ label, used, limit }: UsageStatItem) {
  const pct = usagePercent(used, limit);
  return (
    <div className="rounded-xl border border-border bg-surface2 px-3 py-2.5">
      <p className="text-xs font-medium text-faint">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold font-numeric ${usageTextTone(pct)}`}>
        {used.toLocaleString("de-DE")} / {formatLimit(limit)}
      </p>
    </div>
  );
}
