import { cn } from "@/lib/cn";

interface ToggleProps {
  checked: boolean;
  onChange: (value: boolean) => void;
  label?: string;
  disabled?: boolean;
  id?: string;
}

/** Pill switch styled with design tokens. */
export function Toggle({ checked, onChange, label, disabled, id }: ToggleProps) {
  const button = (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-brand" : "bg-surface2 border border-border2"
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-150",
          checked ? "translate-x-6" : "translate-x-1"
        )}
      />
    </button>
  );

  if (!label) return button;

  return (
    <label className="flex cursor-pointer items-center justify-between gap-3">
      <span className="text-sm text-ink2">{label}</span>
      {button}
    </label>
  );
}
