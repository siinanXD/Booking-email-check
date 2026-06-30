import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { ActivityStatus } from "@/lib/types/api";
import { Card } from "@/shared/ui/Card";
import {
  ACTIVITY_COLORS,
  ACTIVITY_LABELS,
} from "@/features/admin/components/charts/chartTheme";

export function ActivityStatusChart({
  tenants,
}: {
  tenants: { activity_status: ActivityStatus }[];
}) {
  const counts = tenants.reduce(
    (acc, t) => {
      acc[t.activity_status] = (acc[t.activity_status] ?? 0) + 1;
      return acc;
    },
    {} as Record<ActivityStatus, number>
  );

  const data = (["active", "idle", "never"] as ActivityStatus[])
    .map((key) => ({
      name: ACTIVITY_LABELS[key],
      key,
      value: counts[key] ?? 0,
    }))
    .filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <Card>
        <h3 className="mb-2 font-medium text-ink">Mandanten-Aktivität</h3>
        <p className="text-sm text-muted">Noch keine aktiven Mandanten.</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Mandanten-Aktivität</h3>
      <p className="mb-4 text-xs text-muted">
        Aktiv = Sync, Mail, Review oder API-Nutzung in den letzten 7 Tagen
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell key={entry.key} fill={ACTIVITY_COLORS[entry.key]} />
            ))}
          </Pie>
          <Tooltip formatter={(v) => [`${v} Mandant(en)`, "Anzahl"]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
