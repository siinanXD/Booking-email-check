import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { fetchBookings, fetchEmails, type EmailListParams } from "@/lib/api/emails";
import { defaultDateRange, dateRangeQueryParams } from "@/lib/dateRange";
import type { EmailListItem } from "@/lib/types/api";
import { useDebounce } from "@/shared/hooks/useDebounce";
import { DateRangeFilter } from "@/shared/components/DateRangeFilter";
import { EmailDetailSideCard } from "@/shared/components/EmailDetailSideCard";
import { EmailTable } from "@/shared/components/EmailTable";
import { ErrorState } from "@/shared/components/ErrorState";
import { Button } from "@/shared/ui/Button";

type ListMode = "bookings" | "emails";

export function EmailListPage({
  title,
  subtitle,
  params,
  mode = "emails",
}: {
  title: string;
  subtitle?: string;
  params?: EmailListParams;
  mode?: ListMode;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dateRange, setDateRange] = useState(defaultDateRange);
  const [selected, setSelected] = useState<EmailListItem | null>(null);
  const debouncedSearch = useDebounce(search.trim());

  const queryParams: EmailListParams = {
    ...params,
    ...dateRangeQueryParams(dateRange),
    search: debouncedSearch || undefined,
    page,
    limit: 20,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["email-list", mode, queryParams],
    queryFn: () =>
      mode === "bookings" ? fetchBookings(queryParams) : fetchEmails(queryParams),
  });

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
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
        <p className="rounded-xl border border-amber-200/80 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Keine Einträge im gewählten Zeitraum. Neue Mails über „Postfach
          synchronisieren" holen — Buchungen erkennt die KI auch aus normalem
          Gasttext (Name, E-Mail, Buchungswunsch), nicht nur PMS-Mails.
        </p>
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
