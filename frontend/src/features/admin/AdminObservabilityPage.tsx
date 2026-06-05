import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  fetchAdminCostsMetrics,
  fetchAdminPublicConfig,
  fetchAdminTokensMetrics,
} from "@/lib/api/admin";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import {
  TenantCostRankingChart,
  TopCostMailsChart,
} from "@/features/admin/components/charts/ObservabilityCharts";
import { TokenSplitChart } from "@/features/admin/components/charts/TokenSplitChart";
import { CostChart } from "@/shared/components/CostChart";
import { StatCard } from "@/shared/components/StatCard";
import { Card } from "@/shared/ui/Card";

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatTs(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("de-DE");
}

export function AdminObservabilityPage() {
  const { data: costs, isLoading: costsLoading } = useQuery({
    queryKey: ["admin-metrics-costs"],
    queryFn: () => fetchAdminCostsMetrics(30),
    refetchInterval: 60_000,
  });

  const { data: tokens } = useQuery({
    queryKey: ["admin-metrics-tokens"],
    queryFn: () => fetchAdminTokensMetrics(30),
    refetchInterval: 60_000,
  });

  const { data: config } = useQuery({
    queryKey: ["admin-public-config"],
    queryFn: fetchAdminPublicConfig,
  });

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Observability & Kosten"
        description="Alle Mandanten zusammen: API-Kosten, Token-Verbrauch und teure Einzelläufe. Daten stammen aus der mail_metrics-Collection — erfasst wird jede Mail, die durch Klassifikation, Extraktion oder Entwurf gelaufen ist."
        impact="Reine Auswertung — hier änderst du keine Einstellungen. Hohe Kosten? Prüfe unter LLM-Konfiguration Temperatur und Top-K, oder öffne Langfuse-Sessions für einzelne teure Mails."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Plattform-Kosten (30 Tage)"
          value={costsLoading ? "…" : formatUsd(costs?.total_usd ?? 0)}
        />
        <StatCard
          title="Prompt-Tokens"
          value={(tokens?.prompt_tokens ?? 0).toLocaleString("de-DE")}
        />
        <StatCard
          title="Completion-Tokens"
          value={(tokens?.completion_tokens ?? 0).toLocaleString("de-DE")}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-1 text-lg font-medium text-slate-900">
            Kostenverlauf (30 Tage)
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            Tägliche Summe über alle Mandanten — Spitzen deuten auf viele oder komplexe Mails hin
          </p>
          <CostChart
            series={costs?.series ?? []}
            emptyHint="Noch keine plattformweiten API-Kosten erfasst."
          />
        </Card>
        <TokenSplitChart
          promptTokens={tokens?.prompt_tokens ?? 0}
          completionTokens={tokens?.completion_tokens ?? 0}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {costs?.by_account && (
          <TenantCostRankingChart rows={costs.by_account} />
        )}
        {costs?.top_mails && (
          <TopCostMailsChart mails={costs.top_mails} />
        )}
      </div>

      {costs && (
        <p className="text-sm text-slate-600">
          Summe Mandanten: {formatUsd(
            costs.by_account.reduce((s, r) => s + r.cost_usd, 0)
          )}{" "}
          · Nicht zugeordnet: {formatUsd(costs.unassigned_cost_usd ?? 0)} · Gesamt:{" "}
          {formatUsd(costs.total_usd)}
        </p>
      )}

      <Card className="overflow-x-auto">
        <h2 className="mb-1 text-lg font-medium text-slate-900">Kosten pro Mandant</h2>
        <p className="mb-4 text-xs text-slate-500">Tabellarische Detailansicht zum Abgleich mit dem Diagramm</p>
        {!costs?.by_account.length ? (
          <p className="text-sm text-slate-500">Keine Daten.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2 pr-4 font-medium">Mandant</th>
                <th className="pb-2 pr-4 font-medium">Kosten</th>
                <th className="pb-2 pr-4 font-medium">Tokens</th>
                <th className="pb-2 font-medium">Mails</th>
              </tr>
            </thead>
            <tbody>
              {costs.by_account.map((row) => (
                <tr key={row.account_id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">
                    <Link
                      to={`/admin/accounts/${row.account_id}`}
                      className="text-indigo-600 hover:underline"
                    >
                      {row.display_name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">{formatUsd(row.cost_usd)}</td>
                  <td className="py-2 pr-4">
                    {row.total_tokens.toLocaleString("de-DE")}
                  </td>
                  <td className="py-2">{row.mail_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card className="overflow-x-auto">
        <h2 className="mb-1 text-lg font-medium text-slate-900">Teuerste Mails (Top 10)</h2>
        <p className="mb-4 text-xs text-slate-500">
          Langfuse-Links öffnen die Trace-Session zur Fehleranalyse (kein Mail-Inhalt in der Admin-UI)
        </p>
        {!costs?.top_mails.length ? (
          <p className="text-sm text-slate-500">Keine Metriken.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2 pr-4 font-medium">Kosten</th>
                <th className="pb-2 pr-4 font-medium">Tokens</th>
                <th className="pb-2 pr-4 font-medium">Zeit</th>
                <th className="pb-2 font-medium">Langfuse</th>
              </tr>
            </thead>
            <tbody>
              {costs.top_mails.map((mail) => (
                <tr key={mail.correlation_id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{formatUsd(mail.cost_usd)}</td>
                  <td className="py-2 pr-4">
                    {mail.total_tokens.toLocaleString("de-DE")}
                  </td>
                  <td className="py-2 pr-4 text-slate-600">
                    {formatTs(mail.processed_at)}
                  </td>
                  <td className="py-2">
                    {mail.langfuse_session_url ? (
                      <a
                        href={mail.langfuse_session_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-600 hover:underline"
                      >
                        Session
                      </a>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {config && !config.langfuse_tracing_enabled && (
        <p className="text-xs text-slate-500">
          Langfuse-Tracing ist deaktiviert — Session-Links erscheinen erst mit gültigen LANGFUSE_* Keys.
        </p>
      )}
    </div>
  );
}
