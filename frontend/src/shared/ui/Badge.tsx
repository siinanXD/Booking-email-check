const styles: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 ring-1 ring-amber-200/80",
  approved: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/80",
  rejected: "bg-red-50 text-red-700 ring-1 ring-red-200/80",
  discarded: "bg-slate-100 text-slate-500 ring-1 ring-slate-200/80",
  booking: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/80",
  cancellation: "bg-red-50 text-red-700 ring-1 ring-red-200/80",
  change: "bg-sky-50 text-sky-700 ring-1 ring-sky-200/80",
  inquiry: "bg-violet-50 text-violet-700 ring-1 ring-violet-200/80",
  complaint: "bg-orange-50 text-orange-700 ring-1 ring-orange-200/80",
  payment: "bg-amber-50 text-amber-800 ring-1 ring-amber-200/80",
  default: "bg-slate-100 text-slate-600 ring-1 ring-slate-200/80",
};

const dots: Record<string, string> = {
  pending: "bg-amber-400",
  approved: "bg-emerald-500",
  rejected: "bg-red-500",
  discarded: "bg-slate-400",
  booking: "bg-emerald-500",
  cancellation: "bg-red-500",
  change: "bg-sky-500",
  inquiry: "bg-violet-500",
  complaint: "bg-orange-500",
  payment: "bg-amber-500",
  default: "bg-slate-400",
};

export type BadgeTone =
  | "pending"
  | "approved"
  | "rejected"
  | "discarded"
  | "booking"
  | "cancellation"
  | "change"
  | "inquiry"
  | "complaint"
  | "payment"
  | "default";

export function Badge({
  label,
  tone = "default",
  dot = false,
}: {
  label: string;
  // Known tones get autocomplete; arbitrary strings fall back to "default".
  tone?: BadgeTone | (string & {});
  dot?: boolean;
}) {
  const key = styles[tone] ? tone : "default";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[key]}`}
    >
      {dot && (
        <span className={`h-1.5 w-1.5 rounded-full ${dots[key]}`} />
      )}
      {label}
    </span>
  );
}
