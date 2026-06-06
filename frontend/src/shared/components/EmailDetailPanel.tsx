import type { EmailDetail } from "@/lib/types/api";
import { IntentBadge } from "@/shared/components/IntentBadge";
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
        <div className="h-5 w-20 rounded-full bg-slate-100" />
        <div className="h-5 w-16 rounded-full bg-slate-100" />
      </div>
      <div className="h-14 w-full rounded-lg bg-slate-100" />
      <div className="h-32 w-full rounded-lg bg-slate-100" />
    </div>
  );
}

export function EmailDetailPanel({ detail, isLoading, showFullBody }: Props) {
  if (isLoading) return <DetailSkeleton />;

  if (!detail) {
    return (
      <p className="text-sm text-slate-400 italic">Keine Detaildaten verfügbar.</p>
    );
  }

  return (
    <div className="space-y-3 text-sm">
      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-2">
        <IntentBadge intent={detail.intent} />
        {detail.booking_number && (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200/80">
            <Hash size={10} />
            {detail.booking_number}
          </span>
        )}
        {detail.mail_sentiment && (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200/80">
            <MessageSquare size={10} />
            {detail.mail_sentiment}
          </span>
        )}
      </div>

      {/* Summary */}
      {detail.mail_summary && (
        <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Zusammenfassung
          </p>
          <p className="text-xs leading-relaxed text-slate-700">{detail.mail_summary}</p>
        </div>
      )}

      {/* Body */}
      <div className="rounded-lg border border-slate-100 bg-slate-50">
        <p className="border-b border-slate-100 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          E-Mail-Text
        </p>
        <pre className={`overflow-auto px-3 py-2.5 whitespace-pre-wrap text-xs leading-relaxed text-slate-700${showFullBody ? "" : " max-h-44"}`}>
          {detail.body_text}
        </pre>
      </div>

      {/* Draft */}
      {detail.draft_body && (
        <div className="rounded-lg border border-amber-200/80 bg-amber-50/50">
          <p className="flex items-center gap-1.5 border-b border-amber-100 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
            <FileText size={11} />
            Entwurf
          </p>
          <pre className="max-h-40 overflow-auto px-3 py-2.5 whitespace-pre-wrap text-xs leading-relaxed text-amber-900">
            {detail.draft_body}
          </pre>
        </div>
      )}
    </div>
  );
}
