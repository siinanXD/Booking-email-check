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
      <div className="flex rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
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
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
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
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          Alle
        </button>
      </div>

      {/* Custom range */}
      <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 shadow-sm">
        <Calendar size={13} className="text-slate-400" />
        <input
          type="date"
          aria-label="Von"
          max={value.toDate || today()}
          className="bg-transparent text-xs text-slate-600 outline-none focus:text-slate-900"
          value={value.fromDate}
          onChange={(e) => onChange({ ...value, fromDate: e.target.value })}
        />
        <span className="text-slate-300">–</span>
        <input
          type="date"
          aria-label="Bis"
          min={value.fromDate}
          max={today()}
          className="bg-transparent text-xs text-slate-600 outline-none focus:text-slate-900"
          value={value.toDate}
          onChange={(e) => onChange({ ...value, toDate: e.target.value })}
        />
      </div>
    </div>
  );
}
