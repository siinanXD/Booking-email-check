import { IntentBadge } from "@/shared/components/IntentBadge";

type Props = {
  confidence: number | null;
  signals: string[];
  groundingSpan: string | null;
  intent?: string | null;
  escalated?: boolean;
};

const SIGNAL_LABELS: Record<string, string> = {
  booking_ref: "Buchungsnummer",
  guest_name: "Gastname",
  date: "Datum",
};

function signalLabel(key: string): string {
  return SIGNAL_LABELS[key] ?? key;
}

// Circumference for r=24 ≈ 150.8, matching the `ringFill` keyframe range.
const CIRC = 151;

/** „Warum diese Einstufung?“ — confidence ring, signal chips, cited belegstelle. */
export function ClassificationReasonCard({
  confidence,
  signals,
  groundingSpan,
  intent,
  escalated,
}: Props) {
  const pct = confidence != null ? Math.round(confidence * 100) : null;
  const offset =
    confidence != null ? CIRC - Math.max(0, Math.min(1, confidence)) * CIRC : CIRC;

  return (
    <div className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">Warum diese Einstufung?</p>
        {escalated && (
          <span className="rounded-full bg-dangerbg px-2.5 py-0.5 text-xs font-medium text-dangertext">
            Eskaliert
          </span>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Confidence ring */}
        <div className="relative h-16 w-16 flex-shrink-0">
          <svg viewBox="0 0 56 56" className="h-16 w-16 -rotate-90">
            <circle
              cx="28"
              cy="28"
              r="24"
              fill="none"
              stroke="var(--border)"
              strokeWidth="4"
            />
            {confidence != null && (
              <circle
                cx="28"
                cy="28"
                r="24"
                fill="none"
                stroke="var(--brand)"
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray={CIRC}
                strokeDashoffset={offset}
                className="animate-ring-fill"
                style={{ strokeDashoffset: offset }}
              />
            )}
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-numeric text-sm font-bold text-ink">
              {pct != null ? `${pct}%` : "—"}
            </span>
          </div>
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          {intent && <IntentBadge intent={intent} />}
          {/* Signal chips — signals are grounding MISMATCHES. */}
          <div className="flex flex-wrap gap-1.5">
            {signals.length === 0 ? (
              <span className="rounded-full bg-okbg px-2.5 py-0.5 text-xs font-medium text-oktext">
                Vollständig belegt
              </span>
            ) : (
              signals.map((s) => (
                <span
                  key={s}
                  className="rounded-full bg-warnbg px-2.5 py-0.5 text-xs font-medium text-warntext"
                >
                  {signalLabel(s)}
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Cited belegstelle */}
      {groundingSpan && (
        <div className="rounded-xl border border-border bg-surface2 px-3 py-2.5">
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-faint">
            Belegstelle aus der Mail
          </p>
          <p className="text-xs leading-relaxed text-ink2">{groundingSpan}</p>
        </div>
      )}
    </div>
  );
}
