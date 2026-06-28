import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Filter } from "lucide-react";
import { fetchAdminPipeline } from "@/lib/api/admin";
import { Card } from "@/shared/ui/Card";
import { ErrorState } from "@/shared/components/ErrorState";
import { EmptyState } from "@/shared/components/EmptyState";
import type { FunnelStage } from "@/lib/types/api";

const DAYS_OPTIONS = [7, 30, 90] as const;

type Tone = "neutral" | "ok" | "warn" | "danger";

function stageTone(state: string): Tone {
  if (state === "approved") return "ok";
  if (state === "pending_review") return "warn";
  if (state === "rejected" || state === "discarded") return "danger";
  return "neutral";
}

const BAR_BG: Record<Tone, string> = {
  neutral: "bg-brand",
  ok: "bg-[var(--oktext)]",
  warn: "bg-[var(--warntext)]",
  danger: "bg-[var(--dangertext)]",
};

const COUNT_TONE: Record<Tone, string> = {
  neutral: "text-ink",
  ok: "text-oktext",
  warn: "text-warntext",
  danger: "text-dangertext",
};

function StageBar({
  stage,
  total,
  prev,
}: {
  stage: FunnelStage;
  total: number;
  prev: number | null;
}) {
  const tone = stageTone(stage.state);
  const widthPct = total === 0 ? 0 : Math.round((stage.count / total) * 100);
  const dropPct =
    prev != null && prev > 0
      ? Math.round(((prev - stage.count) / prev) * 100)
      : null;

  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium text-ink2">{stage.label}</span>
        <span className="flex items-baseline gap-2">
          {dropPct != null && dropPct > 0 && (
            <span className="text-[11px] font-medium text-faint">
              −{dropPct}%
            </span>
          )}
          <span
            className={`font-numeric font-semibold tabular-nums ${COUNT_TONE[tone]}`}
          >
            {stage.count}
          </span>
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-app">
        <div
          className={`h-full rounded-full ${BAR_BG[tone]}`}
          style={{ width: `${widthPct}%` }}
        />
      </div>
    </div>
  );
}

export function PipelineFunnel() {
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-pipeline", days],
    queryFn: () => fetchAdminPipeline(days),
  });

  const total = data?.funnel.total ?? 0;
  const stages = data?.funnel.states ?? [];

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter size={18} className="text-brandink" />
          <h2 className="font-semibold text-ink">Verarbeitungs-Trichter</h2>
        </div>
        <div className="flex gap-1">
          {DAYS_OPTIONS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDays(d)}
              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                days === d
                  ? "bg-brand text-brandink"
                  : "bg-app text-muted hover:text-ink2"
              }`}
            >
              {d} T
            </button>
          ))}
        </div>
      </div>

      {isError ? (
        <ErrorState
          message="Trichter konnte nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <p className="text-sm text-muted">Lade Trichter…</p>
      ) : stages.length === 0 ? (
        <EmptyState
          bare
          title="Keine Daten im Zeitraum"
          message="In diesem Zeitraum wurden keine Mails verarbeitet."
        />
      ) : (
        <div className="space-y-3">
          {stages.map((stage, i) => (
            <StageBar
              key={stage.state}
              stage={stage}
              total={total}
              prev={i === 0 ? null : stages[i - 1].count}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
