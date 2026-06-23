import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { fetchEmails, type EmailListParams } from "@/lib/api/emails";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import { defaultDateRange, dateRangeQueryParams } from "@/lib/dateRange";
import type { DashboardStats, EmailListItem } from "@/lib/types/api";
import { useDebounce } from "@/shared/hooks/useDebounce";
import { DateRangeFilter } from "@/shared/components/DateRangeFilter";
import { EmailDetailSideCard } from "@/shared/components/EmailDetailSideCard";
import { EmailTable } from "@/shared/components/EmailTable";
import { EmptyState } from "@/shared/components/EmptyState";
import { ErrorState } from "@/shared/components/ErrorState";
import { Button } from "@/shared/ui/Button";

type InboxTab = {
  intent: string;
  label: string;
  countKey?: keyof DashboardStats;
};

const TABS: InboxTab[] = [
  { intent: "", label: "Alle" },
  { intent: "new_booking", label: "Buchungen", countKey: "nav_bookings" },
  { intent: "cancellation", label: "Stornos", countKey: "nav_cancellations" },
  { intent: "change", label: "Änderungen", countKey: "nav_changes" },
  { intent: "guest_inquiry", label: "Nachrichten", countKey: "nav_messages" },
];

export function InboxPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const intent = searchParams.get("intent") ?? "";

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dateRange, setDateRange] = useState(defaultDateRange);
  const [selected, setSelected] = useState<EmailListItem | null>(null);
  const debouncedSearch = useDebounce(search.trim());

  const setIntent = (next: string) => {
    setPage(1);
    setSelected(null);
    setSearchParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        if (next) p.set("intent", next);
        else p.delete("intent");
        return p;
      },
      { replace: true }
    );
  };

  const queryParams: EmailListParams = {
    ...(intent ? { intent, booking_related: true } : {}),
    ...dateRangeQueryParams(dateRange),
    search: debouncedSearch || undefined,
    page,
    limit: 20,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["email-list", queryParams],
    queryFn: () => fetchEmails(queryParams),
  });

  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
    refetchInterval: 30_000,
  });

  const hasDateFilter = Boolean(dateRange.fromDate || dateRange.toDate);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Posteingang</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Eingegangene Mails nach Kategorie — die KI erkennt Buchungen auch aus
          normalem Gasttext.
        </p>
      </div>

      {/* Intent tabs */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex max-w-full overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {TABS.map((t) => {
            const count = t.countKey && stats ? stats[t.countKey] : undefined;
            return (
              <button
                key={t.intent || "all"}
                type="button"
                className={`flex min-h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
                  intent === t.intent
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
                onClick={() => setIntent(t.intent)}
              >
                {t.label}
                {typeof count === "number" && count > 0 && (
                  <span
                    className={`rounded-full px-1.5 text-[10px] font-bold ${
                      intent === t.intent
                        ? "bg-white/25 text-white"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
        <div className="relative min-w-[220px] flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            type="text"
            aria-label="Suche nach Betreff oder Buchungsnummer"
            placeholder="Suche (Betreff, Buchungsnr.)…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-slate-400 transition-all focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-10 text-slate-500">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
          <span className="text-sm">Lade…</span>
        </div>
      ) : isError ? (
        <ErrorState
          message="E-Mails konnten nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : !data?.items.length ? (
        <EmptyState
          title="Keine Einträge gefunden"
          message={
            hasDateFilter
              ? `Zeitraum ${dateRange.fromDate || "Anfang"} – ${
                  dateRange.toDate || "heute"
                }. Neue Mails über „Postfach synchronisieren" auf dem Dashboard holen.`
              : 'Neue Mails über „Postfach synchronisieren" auf dem Dashboard holen — die KI erkennt Buchungen auch aus normalem Gasttext.'
          }
          action={
            hasDateFilter
              ? {
                  label: "Alle anzeigen",
                  onClick: () => {
                    setDateRange({ fromDate: "", toDate: "" });
                    setPage(1);
                  },
                }
              : undefined
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div className="space-y-4">
            <EmailTable
              items={data.items}
              selectedCorrelationId={selected?.correlation_id}
              onRowClick={(item) => setSelected(item)}
            />
            {data.pages > 1 && (
              <div className="flex items-center justify-between text-sm text-slate-600">
                <span className="text-xs text-slate-500">
                  Seite {data.page} von {data.pages} ({data.total} gesamt)
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Zurück
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= data.pages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Weiter
                  </Button>
                </div>
              </div>
            )}
          </div>
          <EmailDetailSideCard selected={selected} />
        </div>
      )}
    </div>
  );
}
