import { INTENT_FILTER_OPTIONS } from "@/lib/intentDisplay";

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function IntentCategoryFilter({ value, onChange }: Props) {
  return (
    <select
      className="rounded-xl border border-border2 bg-surface px-3 py-2 text-sm text-ink"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {INTENT_FILTER_OPTIONS.map((opt) => (
        <option key={opt.value || "all"} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
