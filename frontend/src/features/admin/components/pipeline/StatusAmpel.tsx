import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { fetchAdminStatus } from "@/lib/api/admin";
import { Card } from "@/shared/ui/Card";
import { ErrorState } from "@/shared/components/ErrorState";
import { formatTs } from "@/lib/format";
import type { AdminStatusResponse } from "@/lib/types/api";

type Signal = "ok" | "degraded" | "down";

const DOT_VAR: Record<Signal, string> = {
  ok: "var(--oktext)",
  degraded: "var(--warntext)",
  down: "var(--dangertext)",
};

const OVERALL_TONE: Record<Signal, string> = {
  ok: "bg-okbg text-oktext",
  degraded: "bg-warnbg text-warntext",
  down: "bg-dangerbg text-dangertext",
};

const OVERALL_LABEL: Record<Signal, string> = {
  ok: "Alles in Ordnung",
  degraded: "Eingeschränkt",
  down: "Ausfall",
};

function relativeSync(value: string | null): string {
  if (!value) return "nie";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const diffMin = Math.round((Date.now() - d.getTime()) / 60_000);
  if (diffMin < 1) return "gerade eben";
  if (diffMin < 60) return `vor ${diffMin} min`;
  const diffH = Math.round(diffMin / 60);
  if (diffH < 24) return `vor ${diffH} h`;
  return formatTs(value);
}

function Tile({
  label,
  signal,
  primary,
  hint,
}: {
  label: string;
  signal: Signal;
  primary: string;
  hint?: string;
}) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-border bg-surface px-3 py-2.5">
      <span
        className="mt-1 h-2.5 w-2.5 flex-none rounded-full"
        style={{ background: DOT_VAR[signal] }}
        aria-hidden
      />
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-faint">
          {label}
        </p>
        <p className="text-sm font-semibold text-ink">{primary}</p>
        {hint && <p className="truncate text-[11px] text-muted">{hint}</p>}
      </div>
    </div>
  );
}

function buildTiles(s: AdminStatusResponse) {
  const dbSignal: Signal = s.db.ok ? "ok" : "down";
  const pollSignal: Signal = !s.polling.expected
    ? "ok"
    : s.polling.stale
    ? "degraded"
    : "ok";
  const waSignal: Signal = s.whatsapp_24h.failed > 0 ? "degraded" : "ok";
  const accSignal: Signal = s.accounts.error > 0 ? "degraded" : "ok";
  const intCount =
    (s.integrations.langfuse_configured ? 1 : 0) +
    (s.integrations.sentry_configured ? 1 : 0);
  const intSignal: Signal = intCount === 2 ? "ok" : "degraded";

  return [
    {
      label: "Datenbank",
      signal: dbSignal,
      primary: s.db.ok ? "Verbunden" : "Fehler",
    },
    {
      label: "Polling",
      signal: pollSignal,
      primary: s.polling.stale ? "Verzögert" : "Aktiv",
      hint: `${s.polling.pollable_accounts} Konten · ${relativeSync(
        s.polling.last_sync_at
      )}`,
    },
    {
      label: "WhatsApp 24 h",
      signal: waSignal,
      primary: `${s.whatsapp_24h.sent} gesendet`,
      hint: `${s.whatsapp_24h.failed} fehlgeschlagen · ${s.whatsapp_24h.pending} offen`,
    },
    {
      label: "Konten",
      signal: accSignal,
      primary: `${s.accounts.connected}/${s.accounts.total} verbunden`,
      hint: s.accounts.error > 0 ? `${s.accounts.error} mit Fehler` : "keine Fehler",
    },
    {
      label: "Integrationen",
      signal: intSignal,
      primary: `${intCount}/2 aktiv`,
      hint: `Langfuse ${
        s.integrations.langfuse_configured ? "✓" : "✗"
      } · Sentry ${s.integrations.sentry_configured ? "✓" : "✗"}`,
    },
  ];
}

export function StatusAmpel() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-status"],
    queryFn: fetchAdminStatus,
    refetchInterval: 15_000,
  });

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-brandink" />
          <h2 className="font-semibold text-ink">Systemstatus</h2>
        </div>
        {data && (
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              OVERALL_TONE[data.overall]
            }`}
          >
            {OVERALL_LABEL[data.overall]}
          </span>
        )}
      </div>

      {isError ? (
        <ErrorState
          message="Status konnte nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <p className="text-sm text-muted">Lade Status…</p>
      ) : data ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {buildTiles(data).map((t) => (
            <Tile key={t.label} {...t} />
          ))}
        </div>
      ) : null}
    </Card>
  );
}
