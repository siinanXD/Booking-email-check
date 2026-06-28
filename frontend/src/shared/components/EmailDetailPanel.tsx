import type { EmailDetail } from "@/lib/types/api";
import { IntentBadge } from "@/shared/components/IntentBadge";
import { ClassificationReasonCard } from "@/shared/components/ClassificationReasonCard";
import { Hash, MessageSquare, FileText } from "lucide-react";

type Props = {
  detail: EmailDetail | undefined;
  isLoading?: boolean;
  showFullBody?: boolean;
};

function DetailSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="flex gap-2">
        <div className="h-5 w-20 rounded-full bg-surface2" />
        <div className="h-5 w-16 rounded-full bg-surface2" />
      </div>
      <div className="h-14 w-full rounded-lg bg-surface2" />
      <div className="h-32 w-full rounded-lg bg-surface2" />
    </div>
  );
}

export function EmailDetailPanel({ detail, isLoading, showFullBody }: Props) {
  if (isLoading) return <DetailSkeleton />;

  if (!detail) {
    return (
      <p className="text-sm text-faint italic">Keine Detaildaten verfügbar.</p>
    );
  }

  return (
    <div className="space-y-3 text-sm">
      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-2">
        <IntentBadge intent={detail.intent} />
        {detail.booking_number && (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface2 px-2.5 py-0.5 text-xs font-medium text-ink2 ring-1 ring-border">
            <Hash size={10} />
            {detail.booking_number}
          </span>
        )}
        {detail.mail_sentiment && (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface2 px-2.5 py-0.5 text-xs font-medium text-ink2 ring-1 ring-border">
            <MessageSquare size={10} />
            {detail.mail_sentiment}
          </span>
        )}
      </div>

      {/* Summary */}
      {detail.mail_summary && (
        <div className="rounded-lg border border-border bg-surface2 px-3 py-2.5">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-faint">
            Zusammenfassung
          </p>
          <p className="text-xs leading-relaxed text-ink2">{detail.mail_summary}</p>
        </div>
      )}

      {/* Classification reasoning */}
      <ClassificationReasonCard
        confidence={detail.confidence}
        signals={detail.signals}
        groundingSpan={detail.grounding_span}
        intent={detail.intent}
        escalated={detail.escalated}
      />

      {/* Body */}
      <div className="rounded-lg border border-border bg-surface2">
        <p className="border-b border-border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-faint">
          E-Mail-Text
        </p>
        <pre className={`overflow-auto px-3 py-2.5 whitespace-pre-wrap text-xs leading-relaxed text-ink2${showFullBody ? "" : " max-h-44"}`}>
          {detail.body_text}
        </pre>
      </div>

      {/* Draft */}
      {detail.draft_body && (
        <div className="rounded-lg border border-warntext/30 bg-warnbg/50">
          <p className="flex items-center gap-1.5 border-b border-warntext/20 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-warntext">
            <FileText size={11} />
            Entwurf
          </p>
          <pre className="max-h-40 overflow-auto px-3 py-2.5 whitespace-pre-wrap text-xs leading-relaxed text-warntext">
            {detail.draft_body}
          </pre>
        </div>
      )}
    </div>
  );
}
