import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { fetchAdminMailTrace } from "@/lib/api/admin";
import { ErrorState } from "@/shared/components/ErrorState";
import { intentLabel } from "@/lib/intentDisplay";
import { formatTs } from "@/lib/format";
import type { EmailActivityEvent } from "@/lib/types/api";

interface Props {
  accountId: string;
  correlationId: string;
  onClose: () => void;
}

function Chip({ label, tone }: { label: string; tone: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${tone}`}>
      {label}
    </span>
  );
}

function EventChips({ e }: { e: EmailActivityEvent }) {
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {e.intent && (
        <Chip label={intentLabel(e.intent)} tone="bg-infobg text-infotext" />
      )}
      {e.confidence != null && (
        <Chip
          label={`${Math.round(e.confidence * 100)}%`}
          tone="bg-brandsoft text-brandink"
        />
      )}
      {e.auto_approved && (
        <Chip label="Auto-freigegeben" tone="bg-okbg text-oktext" />
      )}
      {e.escalated && <Chip label="Eskaliert" tone="bg-warnbg text-warntext" />}
      {e.notification_status && (
        <Chip
          label={`Versand: ${e.notification_status}`}
          tone="bg-surface2 text-muted"
        />
      )}
    </div>
  );
}

function TraceEvent({ e }: { e: EmailActivityEvent }) {
  const failed = !!e.error;
  return (
    <li className="relative pl-6">
      <span
        className={`absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full ring-2 ring-surface ${
          failed ? "bg-[var(--dangertext)]" : "bg-brand"
        }`}
        aria-hidden
      />
      <div className="flex items-baseline justify-between gap-3">
        <p
          className={`text-sm font-medium ${
            failed ? "text-dangertext" : "text-ink"
          }`}
        >
          {e.label}
        </p>
        <span className="flex-none text-xs text-muted">{formatTs(e.at)}</span>
      </div>
      <EventChips e={e} />
      {e.error && (
        <p className="mt-1 rounded-lg bg-dangerbg px-2 py-1 text-xs text-dangertext">
          {e.error}
        </p>
      )}
    </li>
  );
}

export function MailTraceModal({ accountId, correlationId, onClose }: Props) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-trace", accountId, correlationId],
    queryFn: () => fetchAdminMailTrace(accountId, correlationId),
    enabled: !!correlationId,
  });

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const events = data?.events ?? [];

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/50 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="trace-modal-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-card-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <h2
              id="trace-modal-title"
              className="text-base font-extrabold text-ink"
            >
              Verlauf
            </h2>
            <p className="truncate font-mono text-xs text-muted">
              {correlationId}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Schließen"
            className="flex-none rounded-lg p-1 text-muted transition-colors hover:bg-app hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {isError ? (
            <ErrorState
              message="Verlauf konnte nicht geladen werden."
              onRetry={() => refetch()}
            />
          ) : isLoading ? (
            <p className="text-sm text-muted">Lade Verlauf…</p>
          ) : events.length === 0 ? (
            <p className="text-sm text-muted">Keine Ereignisse vorhanden.</p>
          ) : (
            <ol className="space-y-4 border-l border-border pl-2">
              {events.map((e, i) => (
                <TraceEvent key={`${e.kind}-${e.at}-${i}`} e={e} />
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
