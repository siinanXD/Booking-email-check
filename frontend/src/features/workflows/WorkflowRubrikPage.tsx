import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchWorkflowNav } from "@/lib/api/workflows";
import { fetchEmails } from "@/lib/api/emails";
import type { EmailListItem } from "@/lib/types/api";
import { EmailDetailSideCard } from "@/shared/components/EmailDetailSideCard";
import { EmailTable } from "@/shared/components/EmailTable";
import { Input } from "@/shared/ui/Input";

export function WorkflowRubrikPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<EmailListItem | null>(null);

  const { data: nav } = useQuery({
    queryKey: ["workflows", "nav"],
    queryFn: fetchWorkflowNav,
  });

  const rubrik = useMemo(
    () => nav?.items.find((w) => w.slug === slug),
    [nav?.items, slug]
  );

  const title = rubrik?.label ?? slug;

  const { data, isLoading } = useQuery({
    queryKey: ["workflow-emails", slug, search, page],
    queryFn: () =>
      fetchEmails({
        workflow_slug: slug,
        search: search || undefined,
        page,
        limit: 20,
      }),
    enabled: Boolean(slug),
  });

  if (!slug) {
    return <p className="text-sm text-slate-600">Rubrik nicht gefunden.</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">{title}</h2>
        {rubrik?.description && (
          <p className="text-sm text-slate-500">{rubrik.description}</p>
        )}
        {!rubrik && (
          <p className="text-sm text-amber-700">
            Dieser Workflow ist nicht aktiv oder wurde entfernt.
          </p>
        )}
      </div>
      <Input
        placeholder="Suche (Betreff, Absender)…"
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
                  className="rounded border px-3 py-1 disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Zurück
                </button>
                <button
                  type="button"
                  className="rounded border px-3 py-1 disabled:opacity-40"
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
          {!isLoading && (data?.total ?? 0) === 0 && (
            <p className="text-sm text-slate-500">
              Noch keine Mails in dieser Rubrik — Routing greift nach Live-Aktivierung.
            </p>
          )}
        </>
      )}
    </div>
  );
}
