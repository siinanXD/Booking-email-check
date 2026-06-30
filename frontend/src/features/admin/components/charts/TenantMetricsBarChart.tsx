import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AdminTenantRow } from "@/lib/types/api";
import { Card } from "@/shared/ui/Card";
import { ADMIN_CHART } from "@/features/admin/components/charts/chartTheme";

export function TenantCostBarChart({ tenants }: { tenants: AdminTenantRow[] }) {
  const data = [...tenants]
    .sort((a, b) => b.costs_30d_usd - a.costs_30d_usd)
    .slice(0, 8)
    .map((t) => ({
      name:
        t.account.display_name.length > 18
          ? `${t.account.display_name.slice(0, 16)}…`
          : t.account.display_name,
      cost: t.costs_30d_usd,
      mails: t.mails_processed_30d,
    }));

  if (data.length === 0) {
    return null;
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Kosten pro Mandant (Top 8)</h3>
      <p className="mb-4 text-xs text-muted">Summe der LLM-API-Kosten der letzten 30 Tage</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            formatter={(v, key) => [
              key === "cost" ? `$${Number(v).toFixed(4)}` : v,
              key === "cost" ? "Kosten" : "Mails",
            ]}
          />
          <Bar dataKey="cost" fill={ADMIN_CHART.indigo} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function TenantMailsBarChart({ tenants }: { tenants: AdminTenantRow[] }) {
  const data = [...tenants]
    .sort((a, b) => b.mails_processed_30d - a.mails_processed_30d)
    .slice(0, 8)
    .map((t) => ({
      name:
        t.account.display_name.length > 14
          ? `${t.account.display_name.slice(0, 12)}…`
          : t.account.display_name,
      mails: t.mails_processed_30d,
    }));

  if (data.every((d) => d.mails === 0)) {
    return null;
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-slate-900">Verarbeitete Mails (Top 8)</h3>
      <p className="mb-4 text-xs text-slate-500">
        Anzahl Mails mit LLM-Pipeline-Lauf in 30 Tagen
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip formatter={(v) => [v, "Mails"]} />
          <Bar dataKey="mails" fill={ADMIN_CHART.violet} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
