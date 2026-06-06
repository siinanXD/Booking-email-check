import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchBookings, fetchEmails, type EmailListParams } from "@/lib/api/emails";
import { defaultDateRange, dateRangeQueryParams } from "@/lib/dateRange";
import type { EmailListItem } from "@/lib/types/api";
import { DateRangeFilter } from "@/shared/components/DateRangeFilter";
import { EmailDetailSideCard } from "@/shared/components/EmailDetailSideCard";
import { EmailTable } from "@/shared/components/EmailTable";
import { Input } from "@/shared/ui/Input";

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

  const queryParams: EmailListParams = {
    ...params,
    ...dateRangeQueryParams(dateRange),
    search: search || undefined,
    page,
    limit: 20,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["email-list", mode, queryParams],
    queryFn: () =>
      mode === "bookings" ? fetchBookings(queryParams) : fetchEmails(queryParams),
  });

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      <DateRangeFilter value={dateRange} onChange={setDateRange} />
      <Input
        placeholder="Suche (Betreff, Buchungsnr.)…"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
      />
      {isLoading ? (
        <p className="text-slate-500">Lade…</p>
      ) : (
        <>
          {!data?.items.length && (
            <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              Keine Einträge im gewählten Zeitraum. Neue Mails über „Postfach
              synchronisieren“ holen — Buchungen erkennt die KI auch aus normalem
              Gasttext (Name, E-Mail, Buchungswunsch), nicht nur PMS-Mails.
            </p>
          )}
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <div className="space-y-4">
              <EmailTable
                items={data?.items ?? []}
                selectedCorrelationId={selected?.correlation_id}
                onRowClick={(item) => setSelected(item)}
              />
              {data && data.pages > 1 && (
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>
                Seite {data.page} von {data.pages} ({data.total} gesamt)
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="min-h-11 rounded border px-4 py-2 disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Zurück
                </button>
                <button
                  type="button"
                  className="min-h-11 rounded border px-4 py-2 disabled:opacity-40"
                  disabled={page >= data.pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Weiter
                </button>
              </div>
            </div>
              )}
            </div>
            <EmailDetailSideCard selected={selected} />
          </div>
        </>
      )}
    </div>
  );
}
