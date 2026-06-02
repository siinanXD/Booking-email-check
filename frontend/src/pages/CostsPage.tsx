import { useQuery } from "@tanstack/react-query";
import { fetchCosts } from "@/api/costs";
import { CostChart } from "@/components/shared/CostChart";
import { StatCard } from "@/components/shared/StatCard";
import { Card } from "@/components/ui/Card";

export function CostsPage() {
  const from = new Date();
  from.setDate(from.getDate() - 30);

  const { data, isLoading } = useQuery({
    queryKey: ["costs-month"],
    queryFn: () =>
      fetchCosts(from.toISOString().slice(0, 10), undefined, "day"),
  });

  const totalMails =
    data?.series.reduce((sum, p) => sum + p.mail_count, 0) ?? 0;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-800">API-Kosten</h2>
      {isLoading ? (
        <p className="text-slate-500">Lade…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              title="Gesamt (30 Tage)"
              value={`$${(data?.total_usd ?? 0).toFixed(4)}`}
            />
            <StatCard title="Mails mit Metriken" value={totalMails} />
            <StatCard
              title="Ø pro Tag"
              value={`$${(
                (data?.total_usd ?? 0) / Math.max(data?.series.length ?? 1, 1)
              ).toFixed(4)}`}
            />
          </div>
          <Card>
            <h3 className="mb-4 font-medium text-slate-800">Verlauf</h3>
            <CostChart
              series={data?.series ?? []}
              emptyHint={
                totalMails === 0
                  ? "Keine Kostendaten: Es wurden noch keine Mails mit LLM-Verarbeitung abgeschlossen. Nach einem Pipeline-Lauf erscheinen hier Tageswerte."
                  : undefined
              }
            />
          </Card>
        </>
      )}
    </div>
  );
}
