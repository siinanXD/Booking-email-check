import { Calendar } from "lucide-react";
import type { DateRangeValue } from "@/lib/dateRange";

type Props = {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
};

function toDateString(daysAgo: number) {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().slice(0, 10);
}

const today = () => new Date().toISOString().slice(0, 10);

const PRESETS = [
  { label: "7T", days: 7 },
  { label: "30T", days: 30 },
  { label: "90T", days: 90 },
];

export function DateRangeFilter({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Quick presets */}
      <div className="flex rounded-xl border border-border bg-surface p-0.5 shadow-card">
        {PRESETS.map(({ label, days }) => {
          const from = toDateString(days);
          const to = today();
          const isActive = value.fromDate === from && value.toDate === to;
          return (
            <button
              key={label}
              type="button"
              onClick={() => onChange({ fromDate: from, toDate: to })}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all duration-150 ${
                isActive
                  ? "bg-brand-gradient text-white shadow-card"
                  : "text-muted hover:text-ink2"
              }`}
            >
              {label}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => onChange({ fromDate: "", toDate: "" })}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all duration-150 ${
            !value.fromDate && !value.toDate
              ? "bg-brand-gradient text-white shadow-card"
              : "text-muted hover:text-ink2"
          }`}
        >
          Alle
        </button>
      </div>

      {/* Custom range */}
      <div className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-1.5 shadow-card">
        <Calendar size={13} className="text-faint" />
        <input
          type="date"
          aria-label="Von"
          max={value.toDate || today()}
          className="bg-transparent text-xs text-ink2 outline-none focus:text-ink font-numeric"
          value={value.fromDate}
          onChange={(e) => onChange({ ...value, fromDate: e.target.value })}
        />
        <span className="text-faint">–</span>
        <input
          type="date"
          aria-label="Bis"
          min={value.fromDate}
          max={today()}
          className="bg-transparent text-xs text-ink2 outline-none focus:text-ink font-numeric"
          value={value.toDate}
          onChange={(e) => onChange({ ...value, toDate: e.target.value })}
        />
      </div>
    </div>
  );
}
