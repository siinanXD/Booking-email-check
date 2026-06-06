import type { DateRangeValue } from "@/lib/dateRange";

type Props = {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
};

export function DateRangeFilter({ value, onChange }: Props) {
  return (
    <fieldset className="grid grid-cols-1 gap-3 sm:flex sm:flex-wrap sm:items-end">
      <legend className="sr-only">Datumsbereich</legend>
      <label className="block w-full text-sm text-slate-600 sm:w-auto">
        Von
        <input
          type="date"
          className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base sm:text-sm focus-visible:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
          value={value.fromDate}
          onChange={(e) => onChange({ ...value, fromDate: e.target.value })}
        />
      </label>
      <label className="block w-full text-sm text-slate-600 sm:w-auto">
        Bis
        <input
          type="date"
          className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base sm:text-sm focus-visible:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
          value={value.toDate}
          onChange={(e) => onChange({ ...value, toDate: e.target.value })}
        />
      </label>
    </fieldset>
  );
}
