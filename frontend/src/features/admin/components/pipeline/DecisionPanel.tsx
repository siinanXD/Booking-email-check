import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { fetchAdminPipeline } from "@/lib/api/admin";
import { Card } from "@/shared/ui/Card";
import { StatCard } from "@/shared/components/StatCard";
import { Badge } from "@/shared/ui/Badge";
import { ErrorState } from "@/shared/components/ErrorState";
import type { ConfidenceBucket } from "@/lib/types/api";

const DAYS_OPTIONS = [7, 30, 90] as const;

function ConfidenceBars({ buckets }: { buckets: ConfidenceBucket[] }) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-faint">
        Konfidenz-Verteilung
      </p>
      {buckets.length === 0 ? (
        <p className="text-xs text-muted">Keine Daten.</p>
      ) : (
        buckets.map((b) => (
          <div key={b.bucket} className="flex items-center gap-2 text-xs">
            <span className="w-16 flex-none font-numeric text-muted">
              {b.bucket}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-app">
              <div
                className="h-full rounded-full bg-brand"
                style={{ width: `${Math.round((b.count / max) * 100)}%` }}
              />
            </div>
            <span className="w-8 flex-none text-right font-numeric tabular-nums text-ink2">
              {b.count}
            </span>
          </div>
        ))
      )}
    </div>
  );
}

export function DecisionPanel() {
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-pipeline", days],
    queryFn: () => fetchAdminPipeline(days),
  });

  const d = data?.decisions;
  const grounding = d?.grounding ?? { ok: 0, fail: 0 };
  const groundTotal = grounding.ok + grounding.fail;
  const groundPct =
    groundTotal === 0 ? 0 : Math.round((grounding.ok / groundTotal) * 100);

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-brandink" />
          <h2 className="font-semibold text-ink">Entscheidungen</h2>
        </div>
        <div className="flex gap-1">
          {DAYS_OPTIONS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setDays(opt)}
              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                days === opt
                  ? "bg-brand text-brandink"
                  : "bg-app text-muted hover:text-ink2"
              }`}
            >
              {opt} T
            </button>
          ))}
        </div>
      </div>

      {isError ? (
        <ErrorState
          message="Entscheidungen konnten nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <p className="text-sm text-muted">Lade Entscheidungen…</p>
      ) : d ? (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard title="Auto-freigegeben" value={d.auto_approved} tone="success" />
            <StatCard title="Manuell freigegeben" value={d.human_approved} tone="success" />
            <StatCard title="Eskaliert" value={d.escalated} tone="warning" hint="überlappt offen" />
            <StatCard title="Abgelehnt" value={d.rejected} tone="danger" />
            <StatCard title="Offen" value={d.pending} tone="info" />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface p-4">
              <ConfidenceBars buckets={d.confidence_buckets} />
            </div>
            <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-faint">
                  Grounding
                </p>
                <p className="mt-1 text-sm text-ink2">
                  <span className="font-numeric font-semibold text-oktext">
                    {grounding.ok}
                  </span>{" "}
                  ok ·{" "}
                  <span className="font-numeric font-semibold text-dangertext">
                    {grounding.fail}
                  </span>{" "}
                  fehlgeschlagen
                </p>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-app">
                  <div
                    className="h-full rounded-full bg-[var(--oktext)]"
                    style={{ width: `${groundPct}%` }}
                  />
                </div>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-faint">
                  Häufigste Quellen-Flags
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {d.top_source_flags.length === 0 ? (
                    <span className="text-xs text-muted">Keine.</span>
                  ) : (
                    d.top_source_flags.map((f) => (
                      <Badge
                        key={f.flag}
                        tone="payment"
                        label={`${f.flag} · ${f.count}`}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </Card>
  );
}
