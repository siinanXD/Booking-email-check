import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type Tone = "default" | "success" | "warning" | "danger" | "info" | "indigo";

const tones: Record<Tone, { iconBg: string; value: string; label: string }> = {
  default: { iconBg: "bg-app text-faint", value: "text-ink", label: "text-faint" },
  indigo: { iconBg: "bg-brandsoft text-brandink", value: "text-ink", label: "text-faint" },
  success: { iconBg: "bg-okbg text-oktext", value: "text-ink", label: "text-faint" },
  warning: { iconBg: "bg-warnbg text-warntext", value: "text-warntext", label: "text-warntext" },
  danger: { iconBg: "bg-dangerbg text-dangertext", value: "text-ink", label: "text-faint" },
  info: { iconBg: "bg-infobg text-infotext", value: "text-ink", label: "text-faint" },
};

export function StatCard({
  title,
  value,
  hint,
  icon,
  highlight,
  to,
  tone = "default",
}: {
  title: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
  highlight?: boolean;
  to?: string;
  tone?: Tone;
}) {
  const resolvedTone: Tone = highlight ? "warning" : tone;
  const t = tones[resolvedTone];

  const inner = (
    <div
      className={`rounded-2xl border bg-surface p-[17px] shadow-card transition-transform duration-200 ${
        highlight ? "border-warnbg" : "border-border"
      } ${to ? "cursor-pointer hover:-translate-y-0.5" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className={`text-[10px] font-bold uppercase tracking-[0.08em] ${t.label}`}>
          {title}
        </span>
        {icon && (
          <span className={`flex h-8 w-8 flex-none items-center justify-center rounded-lg ${t.iconBg}`}>
            {icon}
          </span>
        )}
      </div>
      <p className={`mt-3 font-numeric text-[30px] font-semibold leading-none ${t.value}`}>
        {value}
      </p>
      {hint && (
        <p className={`mt-2 truncate text-[11px] font-bold ${highlight ? "text-warntext" : "text-faint"}`}>
          {hint}
        </p>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="block text-inherit no-underline">
        {inner}
      </Link>
    );
  }
  return inner;
}
