import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/shared/ui/Card";
import { ADMIN_CHART } from "@/features/admin/components/charts/chartTheme";

export function LlmTemperatureChart({
  classify,
  extract,
  draft,
}: {
  classify: number;
  extract: number;
  draft: number;
}) {
  const data = [
    { step: "Klassifikation", temp: classify, color: ADMIN_CHART.indigo },
    { step: "Extraktion", temp: extract, color: ADMIN_CHART.violet },
    { step: "Entwurf", temp: draft, color: ADMIN_CHART.emerald },
  ];

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Temperatur pro Pipeline-Schritt</h3>
      <p className="mb-4 text-xs text-muted">
        0 = deterministisch, höher = kreativer — gilt nach dem Speichern für alle neuen Mails
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="step" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickCount={6} />
          <Tooltip formatter={(v) => [Number(v).toFixed(1), "Temperatur"]} />
          <Bar dataKey="temp" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.step} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
