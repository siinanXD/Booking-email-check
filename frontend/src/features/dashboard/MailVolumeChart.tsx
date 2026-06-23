import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchCosts } from "@/lib/api/costs";
import { defaultDateRange } from "@/lib/dateRange";
import { EmptyState } from "@/shared/components/EmptyState";
import { ErrorState } from "@/shared/components/ErrorState";

const RANGE_DAYS = 30;

function formatDay(value: string): string {
  return new Date(value).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
  });
}

/** Mail volume per day over the last 30 days, reusing the cost day-series. */
export function MailVolumeChart() {
  const range = defaultDateRange(RANGE_DAYS);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["costs", "mail-volume", RANGE_DAYS],
    queryFn: () => fetchCosts(range.fromDate, range.toDate, "day"),
    refetchInterval: 60_000,
  });

  const series = data?.series ?? [];
  const totalMails = series.reduce((sum, p) => sum + (p.mail_count ?? 0), 0);

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-card">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Mail-Volumen
          </p>
          <p className="mt-0.5 text-sm text-slate-500">Letzte {RANGE_DAYS} Tage</p>
        </div>
        {!isLoading && !isError && series.length > 0 && (
          <p className="text-sm font-semibold tabular-nums text-slate-700">
            {totalMails} Mails
          </p>
        )}
      </div>

      {isLoading ? (
        <div className="flex h-[240px] items-center justify-center text-sm text-slate-400">
          Lade…
        </div>
      ) : isError ? (
        <ErrorState
          message="Mail-Volumen konnte nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : series.length === 0 ? (
        <EmptyState
          bare
          title="Noch keine Verlaufsdaten"
          message="Sobald Mails die KI-Pipeline durchlaufen, erscheint hier der Tagesverlauf."
        />
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={series}>
            <defs>
              <linearGradient id="mailFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={formatDay} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals={false} width={32} />
            <Tooltip
              formatter={(value: number) => [`${value}`, "Mails"]}
              labelFormatter={(label: string) =>
                new Date(label).toLocaleDateString("de-DE")
              }
            />
            <Area
              type="monotone"
              dataKey="mail_count"
              stroke="#4f46e5"
              fill="url(#mailFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
