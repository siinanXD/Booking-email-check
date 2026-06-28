import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, CalendarDays, Building2, Mail } from "lucide-react";
import { globalSearch, type SearchHit } from "@/lib/api/search";
import { useDebounce } from "@/shared/hooks/useDebounce";

const GROUPS: {
  key: "bookings" | "properties" | "mails";
  label: string;
  icon: typeof Search;
  tone: string;
}[] = [
  { key: "bookings", label: "Buchungen", icon: CalendarDays, tone: "bg-okbg text-oktext" },
  { key: "properties", label: "Unterkünfte", icon: Building2, tone: "bg-brandsoft text-brandink" },
  { key: "mails", label: "Mails", icon: Mail, tone: "bg-brandsoft text-brandink" },
];

/** Topbar-Suchbutton + ⌘K-Overlay mit gruppierten Treffern. */
export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebounce(query.trim(), 250);
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const { data, isFetching } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => globalSearch(debounced),
    enabled: open && debounced.length >= 2,
    staleTime: 15_000,
  });

  function go(hit: SearchHit) {
    setOpen(false);
    navigate(hit.href);
  }

  const hasResults =
    !!data && (data.bookings.length || data.properties.length || data.mails.length);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Suchen (⌘K)"
        aria-label="Suchen"
        className="flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-border bg-app text-muted transition-colors hover:text-ink"
      >
        <Search size={16} />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[96] flex items-start justify-center bg-slate-950/50 px-4 pt-[90px]"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-[600px] max-w-[92vw] animate-fade-up overflow-hidden rounded-2xl border border-border bg-surface shadow-card-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-border px-4 py-3.5">
              <Search size={18} className="text-muted" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buchungen, Unterkünfte, Mails…"
                className="flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-faint"
              />
              <kbd className="rounded-md border border-border bg-app px-1.5 py-1 font-numeric text-[11px] text-faint">
                esc
              </kbd>
            </div>

            <div className="max-h-[60vh] overflow-auto p-2">
              {debounced.length < 2 && (
                <p className="px-3 py-6 text-center text-[12.5px] text-faint">
                  Tippe mindestens 2 Zeichen…
                </p>
              )}
              {debounced.length >= 2 && isFetching && (
                <p className="px-3 py-6 text-center text-[12.5px] text-faint">Suche…</p>
              )}
              {debounced.length >= 2 && !isFetching && !hasResults && (
                <p className="px-3 py-6 text-center text-[12.5px] text-faint">
                  Keine Treffer für „{debounced}".
                </p>
              )}
              {hasResults &&
                GROUPS.map(({ key, label, icon: Icon, tone }) => {
                  const hits = data?.[key] ?? [];
                  if (!hits.length) return null;
                  return (
                    <div key={key}>
                      <div className="px-2.5 pb-1 pt-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-faint">
                        {label}
                      </div>
                      {hits.map((hit) => (
                        <button
                          key={hit.id}
                          type="button"
                          onClick={() => go(hit)}
                          className="flex w-full items-center gap-3 rounded-lg p-2.5 text-left transition-colors hover:bg-app"
                        >
                          <span
                            className={`flex h-[30px] w-[30px] flex-none items-center justify-center rounded-lg ${tone}`}
                          >
                            <Icon size={15} />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[13px] font-semibold text-ink">
                              {hit.title}
                            </span>
                            {hit.subtitle && (
                              <span className="block truncate text-[11.5px] text-faint">
                                {hit.subtitle}
                              </span>
                            )}
                          </span>
                        </button>
                      ))}
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
