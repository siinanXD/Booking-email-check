import type { EmailDetail } from "@/lib/types/api";
import { IntentBadge } from "@/shared/components/IntentBadge";

type Props = {
  detail: EmailDetail | undefined;
  isLoading?: boolean;
};

export function EmailDetailPanel({ detail, isLoading }: Props) {
  if (isLoading) {
    return <p className="text-sm text-slate-500">Lade Detail…</p>;
  }
  if (!detail) {
    return <p className="text-sm text-slate-500">Keine Detaildaten.</p>;
  }
  return (
    <div className="space-y-3 text-sm">
      {detail.booking_number && (
        <p className="text-sm font-semibold text-slate-800">
          Buchungsnummer: {detail.booking_number}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <IntentBadge intent={detail.intent} />
        {detail.mail_sentiment && (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
            Stimmung: {detail.mail_sentiment}
          </span>
        )}
      </div>
      {detail.mail_summary && (
        <p className="rounded bg-slate-50 p-2 text-slate-700">{detail.mail_summary}</p>
      )}
      <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">
        {detail.body_text}
      </pre>
      {detail.draft_body && (
        <div>
          <p className="text-xs font-medium uppercase text-slate-500">Entwurf</p>
          <pre className="mt-1 whitespace-pre-wrap rounded border p-2 text-xs">
            {detail.draft_body}
          </pre>
        </div>
      )}
    </div>
  );
}
