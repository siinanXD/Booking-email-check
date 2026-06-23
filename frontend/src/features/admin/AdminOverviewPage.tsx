import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpDown } from "lucide-react";
import { fetchAdminOverview } from "@/lib/api/admin";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { ActivityStatusChart } from "@/features/admin/components/charts/ActivityStatusChart";
import {
  TenantCostBarChart,
  TenantMailsBarChart,
} from "@/features/admin/components/charts/TenantMetricsBarChart";
import { ActivityBadge } from "@/features/admin/components/ActivityBadge";
import { ErrorState } from "@/shared/components/ErrorState";
import { StatCard } from "@/shared/components/StatCard";
import { Card } from "@/shared/ui/Card";
import { formatTs } from "@/lib/format";

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

type SortKey = "name" | "cost" | "mails" | "sync";

type TenantRow = {
  account: { display_name: string; contact_email: string };
  costs_30d_usd: number;
  mails_processed_30d: number;
  last_sync_at: string | null;
};

function compareTenants(a: TenantRow, b: TenantRow, key: SortKey): number {
  if (key === "name") {
    return a.account.display_name.localeCompare(b.account.display_name);
  }
  if (key === "cost") return a.costs_30d_usd - b.costs_30d_usd;
  if (key === "mails") return a.mails_processed_30d - b.mails_processed_30d;
  return (a.last_sync_at ?? "").localeCompare(b.last_sync_at ?? "");
}

function SortHeader({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  sort: { key: SortKey; dir: "asc" | "desc" };
  onSort: (key: SortKey) => void;
}) {
  const active = sort.key === sortKey;
  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      className={`inline-flex items-center gap-1 font-medium ${
        active ? "text-indigo-600" : "text-slate-500 hover:text-slate-800"
      }`}
    >
      {label}
      <ArrowUpDown size={12} className={active ? "" : "opacity-40"} aria-hidden />
      {active && (
        <span className="sr-only">
          {sort.dir === "asc" ? "aufsteigend" : "absteigend"}
        </span>
      )}
    </button>
  );
}

export function AdminOverviewPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: fetchAdminOverview,
    refetchInterval: 60_000,
  });

  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "cost",
    dir: "desc",
  });

  const toggleSort = (key: SortKey) =>
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "name" ? "asc" : "desc" }
    );

  const visibleTenants = useMemo(() => {
    const q = search.trim().toLowerCase();
    const rows = (data?.tenants ?? []).filter(
      (t) =>
        !q ||
        t.account.display_name.toLowerCase().includes(q) ||
        t.account.contact_email.toLowerCase().includes(q)
    );
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => dir * compareTenants(a, b, sort.key));
  }, [data, search, sort]);

  const activeTenantCostSum =
    data?.tenants.reduce((sum, t) => sum + t.costs_30d_usd, 0) ?? 0;
  const costGap =
    data != null ? Math.abs(data.total_cost_usd_30d - activeTenantCostSum) : 0;
  const hasCostGap = costGap > 0.0001;

  if (isLoading) {
    return <p className="text-sm text-slate-500">Lade Plattform-Übersicht…</p>;
  }

  if (error || !data) {
    return <ErrorState message="Übersicht konnte nicht geladen werden." />;
  }

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Plattform-Übersicht"
        description="Hier siehst du auf einen Blick, wie viele Mandanten registriert sind, wer die Plattform aktiv nutzt und welche LLM-Kosten in den letzten 30 Tagen entstanden sind. Die Aktivitäts-Ampel basiert auf Mail-Sync, empfangenen Mails, Reviews oder API-Nutzung."
        impact="Du änderst hier nichts direkt — nutze die Tabelle für Details pro Mandant oder wechsle zu Diagnose/Observability, wenn du Verbindungen testen oder Kosten vertiefen willst."
      />

      {hasCostGap && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <strong>Hinweis:</strong> Gesamtkosten ({formatUsd(data.total_cost_usd_30d)})
          weichen von der Summe aktiver Mandanten ({formatUsd(activeTenantCostSum)}) ab —
          Differenz {formatUsd(costGap)}. Mögliche Ursache: Kosten von Mandanten mit Status
          „pending/rejected" oder Metriken ohne Mandantenzuordnung. Details unter{" "}
          <a href="/admin/observability" className="underline">
            Observability
          </a>
          .
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Mandanten gesamt"
          value={data.total_accounts}
          hint={`${data.active_accounts} aktiv · ${data.pending_accounts} ausstehend`}
        />
        <StatCard
          title="Aktive Mandanten (7 Tage)"
          value={data.active_users_7d}
          hint="Sync, Mails, Reviews oder API in 7 Tagen"
        />
        <StatCard
          title="Kosten (30 Tage)"
          value={formatUsd(data.total_cost_usd_30d)}
          hint={`${data.mails_processed_30d} verarbeitete Mails`}
        />
        <StatCard
          title="Tokens (30 Tage)"
          value={data.total_tokens_30d.toLocaleString("de-DE")}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ActivityStatusChart tenants={data.tenants} />
        <TenantCostBarChart tenants={data.tenants} />
      </div>

      <TenantMailsBarChart tenants={data.tenants} />

      <Card className="overflow-x-auto">
        <h2 className="mb-1 text-lg font-medium text-slate-900">Mandanten im Detail</h2>
        <p className="mb-3 text-xs text-slate-500">
          Spaltenkopf klicken zum Sortieren — „Details“ öffnet DB-Counts, Benutzer und Postfach-Status
        </p>
        <div className="mb-4 max-w-sm">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Mandant suchen (Name oder E-Mail)…"
            aria-label="Mandant suchen"
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
        </div>
        {data.tenants.length === 0 ? (
          <p className="text-sm text-slate-500">Keine aktiven Mandanten.</p>
        ) : visibleTenants.length === 0 ? (
          <p className="text-sm text-slate-500">Keine Treffer für die Suche.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th scope="col" className="pb-2 pr-4 font-medium">
                  <SortHeader label="Name" sortKey="name" sort={sort} onSort={toggleSort} />
                </th>
                <th scope="col" className="pb-2 pr-4 font-medium">Aktivität</th>
                <th scope="col" className="pb-2 pr-4 font-medium">
                  <SortHeader label="Kosten 30d" sortKey="cost" sort={sort} onSort={toggleSort} />
                </th>
                <th scope="col" className="pb-2 pr-4 font-medium">
                  <SortHeader label="Mails 30d" sortKey="mails" sort={sort} onSort={toggleSort} />
                </th>
                <th scope="col" className="pb-2 pr-4 font-medium">
                  <SortHeader label="Letzter Sync" sortKey="sync" sort={sort} onSort={toggleSort} />
                </th>
                <th scope="col" className="pb-2 font-medium">
                  <span className="sr-only">Aktionen</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleTenants.map((row) => (
                <tr key={row.account.id} className="border-b border-slate-100">
                  <td className="py-3 pr-4">
                    <div className="font-medium text-slate-900">
                      {row.account.display_name}
                    </div>
                    <div className="text-xs text-slate-500">
                      {row.account.contact_email}
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <ActivityBadge status={row.activity_status} />
                  </td>
                  <td className="py-3 pr-4">{formatUsd(row.costs_30d_usd)}</td>
                  <td className="py-3 pr-4">{row.mails_processed_30d}</td>
                  <td className="py-3 pr-4 text-slate-600">
                    {formatTs(row.last_sync_at)}
                  </td>
                  <td className="py-3">
                    <Link
                      to={`/admin/accounts/${row.account.id}`}
                      className="text-indigo-600 hover:underline"
                    >
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
