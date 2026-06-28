import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { AccountListItem } from "@/lib/types/api";
import { Card } from "@/shared/ui/Card";
import {
  STATUS_COLORS,
  STATUS_LABELS,
} from "@/features/admin/components/charts/chartTheme";

export function AccountStatusChart({ accounts }: { accounts: AccountListItem[] }) {
  const counts = accounts.reduce(
    (acc, a) => {
      acc[a.status] = (acc[a.status] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const data = Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      key,
      name: STATUS_LABELS[key] ?? key,
      value,
    }));

  if (data.length === 0) {
    return null;
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Account-Status</h3>
      <p className="mb-4 text-xs text-muted">Verteilung aller registrierten Mandanten</p>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={75}
          >
            {data.map((entry) => (
              <Cell key={entry.key} fill={STATUS_COLORS[entry.key] ?? "var(--muted)"} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => [`${v} Account(s)`, "Anzahl"]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
