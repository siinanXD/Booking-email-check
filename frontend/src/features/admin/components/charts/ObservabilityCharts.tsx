import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AdminAccountCostRow } from "@/lib/types/api";
import { Card } from "@/shared/ui/Card";
import { ADMIN_CHART } from "@/features/admin/components/charts/chartTheme";

export function TenantCostRankingChart({
  rows,
}: {
  rows: AdminAccountCostRow[];
}) {
  const data = rows.slice(0, 10).map((r) => ({
    name:
      r.display_name.length > 16
        ? `${r.display_name.slice(0, 14)}…`
        : r.display_name,
    cost: r.cost_usd,
    tokens: r.total_tokens,
  }));

  if (data.length === 0) {
    return null;
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Kosten-Ranking</h3>
      <p className="mb-4 text-xs text-muted">
        Mandanten mit den höchsten API-Kosten — Klick in der Tabelle für Details
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v) => [`$${Number(v).toFixed(4)}`, "Kosten"]} />
          <Bar dataKey="cost" fill={ADMIN_CHART.indigo} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function TopCostMailsChart({
  mails,
}: {
  mails: { correlation_id: string; cost_usd: number }[];
}) {
  const data = mails.slice(0, 8).map((m, i) => ({
    name: `#${i + 1}`,
    cost: m.cost_usd,
    id: m.correlation_id.slice(0, 8),
  }));

  if (data.length === 0) {
    return null;
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Teuerste Mails</h3>
      <p className="mb-4 text-xs text-muted">
        Einzelne Mail-Läufe mit den höchsten LLM-Kosten
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v) => [`$${Number(v).toFixed(4)}`, "Kosten"]}
            labelFormatter={(_, payload) => {
              const item = payload?.[0]?.payload as { id?: string } | undefined;
              return item?.id ? `Mail ${item.id}…` : "";
            }}
          />
          <Bar dataKey="cost" fill={ADMIN_CHART.rose} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
