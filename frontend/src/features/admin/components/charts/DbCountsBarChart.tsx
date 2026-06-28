import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/shared/ui/Card";
import { ADMIN_CHART } from "@/features/admin/components/charts/chartTheme";

const COLLECTION_LABELS: Record<string, string> = {
  emails: "E-Mails",
  bookings: "Buchungen",
  guests: "Gäste",
  properties: "Objekte",
  conversations: "Konversationen",
  chunks: "Chunks",
  embeddings: "Embeddings",
  reviews: "Reviews",
};

export function DbCountsBarChart({ counts }: { counts: Record<string, number> }) {
  const data = Object.entries(counts)
    .map(([key, value]) => ({
      name: COLLECTION_LABELS[key] ?? key,
      count: value,
    }))
    .sort((a, b) => b.count - a.count);

  if (data.every((d) => d.count === 0)) {
    return (
      <Card>
        <h3 className="mb-2 font-medium text-ink">Datenbestand</h3>
        <p className="text-sm text-muted">Noch keine Domänendaten für diesen Mandanten.</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="mb-1 font-medium text-ink">Datenbestand im Mandanten</h3>
      <p className="mb-4 text-xs text-muted">
        Dokumente pro MongoDB-Collection — zeigt Nutzungsintensität
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number) => [v.toLocaleString("de-DE"), "Einträge"]} />
          <Bar dataKey="count" fill={ADMIN_CHART.violet} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
