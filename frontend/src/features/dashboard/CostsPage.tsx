import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Mail, DollarSign } from "lucide-react";
import { fetchCosts } from "@/lib/api/costs";
import { CostChart } from "@/shared/components/CostChart";
import { StatCard } from "@/shared/components/StatCard";
import { Card } from "@/shared/ui/Card";

export function CostsPage() {
  const from = new Date();
  from.setDate(from.getDate() - 30);

  const { data, isLoading } = useQuery({
    queryKey: ["costs-month"],
    queryFn: () =>
      fetchCosts(from.toISOString().slice(0, 10), undefined, "day"),
  });

  const PERIOD_DAYS = 30;
  const totalMails =
    data?.series.reduce((sum, p) => sum + p.mail_count, 0) ?? 0;
  const avgPerDay = (data?.total_usd ?? 0) / PERIOD_DAYS;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">API-Kosten</h2>
        <p className="mt-0.5 text-sm text-slate-500">LLM-Nutzung der letzten 30 Tage</p>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-10 text-slate-500">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
          <span className="text-sm">Lade…</span>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              title="Gesamt (30 Tage)"
              value={`$${(data?.total_usd ?? 0).toFixed(4)}`}
              icon={<DollarSign size={20} />}
            />
            <StatCard
              title="Mails mit Metriken"
              value={totalMails}
              icon={<Mail size={20} />}
            />
            <StatCard
              title="Ø pro Tag"
              value={`$${avgPerDay.toFixed(4)}`}
              icon={<TrendingUp size={20} />}
            />
          </div>
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-800">Kostenverlauf</h3>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500">
                30 Tage
              </span>
            </div>
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
