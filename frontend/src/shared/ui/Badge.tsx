const styles: Record<string, string> = {
  pending: "bg-warnbg text-warntext",
  approved: "bg-okbg text-oktext",
  rejected: "bg-dangerbg text-dangertext",
  discarded: "bg-app text-muted",
  booking: "bg-okbg text-oktext",
  cancellation: "bg-dangerbg text-dangertext",
  change: "bg-infobg text-infotext",
  inquiry: "bg-inquirybg text-inquirytext",
  complaint: "bg-dangerbg text-dangertext",
  payment: "bg-warnbg text-warntext",
  escalated: "bg-dangerbg text-dangertext",
  default: "bg-app text-muted",
};

const dots: Record<string, string> = {
  pending: "bg-warntext",
  approved: "bg-oktext",
  rejected: "bg-dangertext",
  discarded: "bg-muted",
  booking: "bg-oktext",
  cancellation: "bg-dangertext",
  change: "bg-infotext",
  inquiry: "bg-inquirytext",
  complaint: "bg-dangertext",
  payment: "bg-warntext",
  escalated: "bg-dangertext",
  default: "bg-muted",
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
  | "escalated"
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
