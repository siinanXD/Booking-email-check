import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Card } from "@/shared/ui/Card";
import { ADMIN_CHART } from "@/features/admin/components/charts/chartTheme";

export function TokenSplitChart({
  promptTokens,
  completionTokens,
}: {
  promptTokens: number;
  completionTokens: number;
}) {
  const total = promptTokens + completionTokens;
  if (total === 0) {
    return (
      <Card>
        <h3 className="mb-2 font-medium text-slate-900">Token-Verteilung</h3>
        <p className="text-sm text-slate-500">Noch keine Token-Daten erfasst.</p>
      </Card>
    );
  }

  const data = [
    { name: "Prompt-Tokens", value: promptTokens, color: ADMIN_CHART.indigo },
    { name: "Completion-Tokens", value: completionTokens, color: ADMIN_CHART.emerald },
  ];

  return (
    <Card>
      <h3 className="mb-1 font-medium text-slate-900">Token-Verteilung (30 Tage)</h3>
      <p className="mb-4 text-xs text-slate-500">
        Eingabe vs. Modell-Antwort — hilft bei Kosten-Optimierung
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v) => [Number(v).toLocaleString("de-DE"), "Tokens"]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
