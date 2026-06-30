import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CalendarDays, Download } from "lucide-react";
import {
  downloadTasksIcs,
  downloadTasksXlsx,
  fetchPartners,
  fetchTasks,
  updateTask,
  type TaskFilters,
} from "@/lib/api/cleaning";
import { PartnerManager } from "@/features/cleaning/PartnerManager";
import { STATUS_OPTIONS, toneFor } from "@/features/cleaning/cleaningStatus";
import { toast } from "@/shared/feedback/toastStore";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

type Tab = "tasks" | "partners";

function fmt(value?: string | null): string {
  if (!value) return "—";
  const [y, m, d] = value.split("-");
  return d ? `${d}.${m}.${y}` : value;
}

export function PutzplanPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("tasks");
  const [filters, setFilters] = useState<TaskFilters>({});
  const [downloading, setDownloading] = useState(false);
  const [openHistory, setOpenHistory] = useState<string | null>(null);

  const { data: tasks, isLoading } = useQuery({
    queryKey: ["cleaning-tasks", filters],
    queryFn: () => fetchTasks(filters),
  });
  const { data: partners } = useQuery({
    queryKey: ["cleaning-partners"],
    queryFn: fetchPartners,
  });

  const mutate = useMutation({
    mutationFn: (vars: {
      taskId: string;
      status?: string;
      partner_id?: string | null;
    }) => updateTask(vars.taskId, { status: vars.status, partner_id: vars.partner_id }),
    onSuccess: () => {
      toast.success("Auftrag aktualisiert.");
      void queryClient.invalidateQueries({ queryKey: ["cleaning-tasks"] });
    },
  });

  const handleExport = async (kind: "xlsx" | "ics") => {
    setDownloading(true);
    try {
      await (kind === "ics"
        ? downloadTasksIcs(filters)
        : downloadTasksXlsx(filters));
    } catch {
      toast.error("Export fehlgeschlagen.");
    } finally {
      setDownloading(false);
    }
  };

  const activePartners = (partners?.items ?? []).filter((p) => p.active);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Putzplan</h1>
        <div className="flex gap-2">
          <Button
            variant={tab === "tasks" ? "primary" : "ghost"}
            size="sm"
            onClick={() => setTab("tasks")}
          >
            Aufträge
          </Button>
          <Button
            variant={tab === "partners" ? "primary" : "ghost"}
            size="sm"
            onClick={() => setTab("partners")}
          >
            Putzpartner
          </Button>
        </div>
      </div>

      {tab === "partners" ? (
        <PartnerManager />
      ) : (
        <>
          <Card>
            <div className="flex flex-wrap items-end gap-3">
              <label className="text-sm">
                <span className="mb-1 block text-oktext/70">Status</span>
                <select
                  className="rounded-md border border-oktext/20 bg-transparent px-3 py-2"
                  value={filters.status ?? ""}
                  onChange={(e) =>
                    setFilters({ ...filters, status: e.target.value || undefined })
                  }
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <Input
                label="Wohnung"
                value={filters.property_name ?? ""}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    property_name: e.target.value || undefined,
                  })
                }
              />
              <Input
                label="Putztermin von"
                type="date"
                value={filters.from ?? ""}
                onChange={(e) =>
                  setFilters({ ...filters, from: e.target.value || undefined })
                }
              />
              <Input
                label="bis"
                type="date"
                value={filters.to ?? ""}
                onChange={(e) =>
                  setFilters({ ...filters, to: e.target.value || undefined })
                }
              />
              <Button
                variant="outline"
                onClick={() => handleExport("xlsx")}
                loading={downloading}
              >
                <Download className="mr-1 h-4 w-4" /> Als Excel
              </Button>
              <Button
                variant="outline"
                onClick={() => handleExport("ics")}
                loading={downloading}
              >
                <CalendarDays className="mr-1 h-4 w-4" /> Als Kalender
              </Button>
            </div>
          </Card>

          {isLoading ? (
            <Card>Lädt…</Card>
          ) : (tasks?.items.length ?? 0) === 0 ? (
            <Card>Keine Putzaufträge für diese Filter.</Card>
          ) : (
            <div className="space-y-2">
              {tasks?.items.map((t) => (
                <Card key={t.task_id}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">
                          {t.property_name ?? "—"}
                          {t.room_number ? ` · Zimmer ${t.room_number}` : ""}
                        </span>
                        <Badge label={t.status_label} tone={toneFor(t.status)} dot />
                      </div>
                      <div className="text-sm text-oktext/70">
                        Putztermin {fmt(t.cleaning_date)} · Gast {t.guest_name ?? "—"}
                        {t.partner_name ? ` · ${t.partner_name}` : ""}
                      </div>
                      {t.last_notification_status === "failed" && (
                        <div className="text-sm text-dangertext">
                          WhatsApp fehlgeschlagen
                        </div>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <select
                        className="rounded-md border border-oktext/20 bg-transparent px-2 py-1 text-sm"
                        value={t.partner_id ?? ""}
                        onChange={(e) =>
                          mutate.mutate({
                            taskId: t.task_id,
                            partner_id: e.target.value || null,
                          })
                        }
                      >
                        <option value="">Partner zuweisen…</option>
                        {activePartners.map((p) => (
                          <option key={p.partner_id} value={p.partner_id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                      {t.status !== "done" && t.status !== "cancelled" && (
                        <Button
                          size="sm"
                          onClick={() =>
                            mutate.mutate({ taskId: t.task_id, status: "done" })
                          }
                        >
                          Erledigt
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setOpenHistory(
                            openHistory === t.task_id ? null : t.task_id
                          )
                        }
                      >
                        Verlauf
                      </Button>
                    </div>
                  </div>
                  {openHistory === t.task_id && (
                    <ul className="mt-3 space-y-1 border-t border-oktext/10 pt-3 text-xs text-oktext/70">
                      {(t.status_history ?? []).map((ev, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="tabular-nums">
                            {ev.at?.slice(0, 16).replace("T", " ") ?? ""}
                          </span>
                          <span className="font-medium">{ev.status}</span>
                          <span>· {ev.source}</span>
                          {ev.note ? <span>· {ev.note}</span> : null}
                        </li>
                      ))}
                      {(t.status_history ?? []).length === 0 && (
                        <li>Kein Verlauf.</li>
                      )}
                    </ul>
                  )}
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
