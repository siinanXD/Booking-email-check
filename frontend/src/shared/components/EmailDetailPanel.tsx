import type { EmailDetail, EmailListItem } from "@/lib/types/api";
import { IntentBadge } from "@/shared/components/IntentBadge";

type Props = {
  detail: EmailDetail | EmailListItem | undefined;
  isLoading?: boolean;
  /** Voller Mailtext mit großem Scrollbereich (Listen-Navigation). */
  showFullBody?: boolean;
};

function formatReceivedAt(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("de-DE");
}

export function EmailDetailPanel({
  detail,
  isLoading,
  showFullBody = false,
}: Props) {
  if (isLoading) {
    return <p className="text-sm text-slate-500">Lade Detail…</p>;
  }
  if (!detail) {
    return <p className="text-sm text-slate-500">Keine Detaildaten.</p>;
  }

  const emailDetail = "body_text" in detail ? detail : undefined;
  const receivedAt = formatReceivedAt(detail.received_at);
  const bodyText = emailDetail?.body_text?.trim();
  const bodyClass = showFullBody
    ? "max-h-[min(70vh,48rem)] overflow-auto whitespace-pre-wrap rounded border border-slate-200 bg-slate-50 p-3 text-sm leading-relaxed text-slate-800"
    : "max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs";

  return (
    <div className="space-y-3 text-sm">
      <div className="space-y-1 border-b border-slate-100 pb-3">
        <h3 className="font-medium text-slate-900">{detail.subject || "—"}</h3>
        <p>
          <span className="text-slate-500">Von: </span>
          {detail.from_address || "—"}
        </p>
        {emailDetail?.to_addresses?.length ? (
          <p>
            <span className="text-slate-500">An: </span>
            {emailDetail.to_addresses.join(", ")}
          </p>
        ) : null}
        {receivedAt && (
          <p>
            <span className="text-slate-500">Empfangen: </span>
            {receivedAt}
          </p>
        )}
      </div>
      {detail.booking_number && (
        <p className="font-semibold text-slate-800">
          Buchungsnummer: {detail.booking_number}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <IntentBadge intent={detail.intent} />
        {emailDetail?.mail_sentiment && (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
            Stimmung: {emailDetail.mail_sentiment}
          </span>
        )}
      </div>
      {emailDetail?.mail_summary && (
        <p className="rounded bg-slate-50 p-2 text-slate-700">
          {emailDetail.mail_summary}
        </p>
      )}
      <div>
        <p className="mb-1 text-xs font-medium uppercase text-slate-500">
          E-Mail-Inhalt
        </p>
        {bodyText ? (
          <pre className={bodyClass}>{bodyText}</pre>
        ) : (
          <p className="text-sm text-slate-500">Kein Mailtext verfügbar.</p>
        )}
      </div>
      {emailDetail?.draft_body && (
        <div>
          <p className="text-xs font-medium uppercase text-slate-500">Entwurf</p>
          <pre className="mt-1 whitespace-pre-wrap rounded border p-2 text-xs">
            {emailDetail.draft_body}
          </pre>
        </div>
      )}
      {emailDetail?.approved_body && (
        <div>
          <p className="text-xs font-medium uppercase text-slate-500">
            Freigegebene Antwort
          </p>
          <pre className="mt-1 whitespace-pre-wrap rounded border border-green-200 bg-green-50 p-2 text-xs">
            {emailDetail.approved_body}
          </pre>
        </div>
      )}
    </div>
  );
}
