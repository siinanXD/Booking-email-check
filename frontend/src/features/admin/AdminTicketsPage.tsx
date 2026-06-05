import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  fetchAdminSupportConfig,
  fetchAdminSupportTickets,
  patchAdminSupportTicket,
  retryAdminSupportTicketWhatsApp,
  saveAdminSupportConfig,
} from "@/lib/api/support";
import type {
  AdminSupportTicketResponse,
  SupportTicketStatus,
  SupportTicketUrgency,
} from "@/lib/types/api-support";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

const STATUS_LABELS: Record<SupportTicketStatus, string> = {
  open: "Offen",
  in_progress: "In Bearbeitung",
  resolved: "Erledigt",
  closed: "Geschlossen",
};

const URGENCY_LABELS: Record<SupportTicketUrgency, string> = {
  low: "Niedrig",
  normal: "Normal",
  high: "Hoch",
  critical: "Kritisch",
};

function urgencyClass(u: SupportTicketUrgency): string {
  if (u === "critical") return "text-red-700 bg-red-50";
  if (u === "high") return "text-orange-700 bg-orange-50";
  if (u === "low") return "text-slate-600 bg-slate-50";
  return "text-slate-700 bg-slate-100";
}

export function AdminTicketsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<SupportTicketStatus | "">("");
  const [highOnly, setHighOnly] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [adminNote, setAdminNote] = useState("");
  const [waPhone, setWaPhone] = useState("");
  const [waTemplate, setWaTemplate] = useState("");

  const { data: tickets } = useQuery({
    queryKey: ["admin-support-tickets", statusFilter, highOnly],
    queryFn: () =>
      fetchAdminSupportTickets({
        status: statusFilter || undefined,
        urgency: highOnly ? "high" : undefined,
      }),
    refetchInterval: 30_000,
  });

  const { data: config } = useQuery({
    queryKey: ["admin-support-config"],
    queryFn: fetchAdminSupportConfig,
  });

  const selected = useMemo(
    () => tickets?.items.find((t) => t.ticket_id === selectedId) ?? null,
    [tickets, selectedId]
  );

  const patchMut = useMutation({
    mutationFn: (args: { id: string; status?: SupportTicketStatus; note?: string }) =>
      patchAdminSupportTicket(args.id, {
        status: args.status,
        admin_note: args.note,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-support-tickets"] });
    },
  });

  const retryMut = useMutation({
    mutationFn: retryAdminSupportTicketWhatsApp,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-support-tickets"] });
    },
  });

  const configMut = useMutation({
    mutationFn: () =>
      saveAdminSupportConfig({
        platform_admin_whatsapp_e164: waPhone.trim(),
        whatsapp_template_support_ticket: waTemplate.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-support-config"] });
    },
  });

  function openDetail(ticket: AdminSupportTicketResponse) {
    setSelectedId(ticket.ticket_id);
    setAdminNote(ticket.admin_note ?? "");
  }

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Support-Tickets"
        description="Mandanten-Anfragen an den Plattform-Betreiber. Bei neuen Tickets wird optional eine WhatsApp-Benachrichtigung an die Admin-Nummer gesendet."
        impact="Status und Admin-Notizen helfen beim Abarbeiten. WhatsApp-Template muss in Meta genehmigt sein."
      />

      <Card className="space-y-3">
        <h2 className="text-sm font-medium text-slate-900">WhatsApp für Ticket-Benachrichtigungen</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            placeholder="+491701234567"
            value={waPhone || config?.platform_admin_whatsapp_e164 || ""}
            onChange={(e) => setWaPhone(e.target.value)}
          />
          <Input
            placeholder="platform_support_ticket_de"
            value={waTemplate || config?.whatsapp_template_support_ticket || ""}
            onChange={(e) => setWaTemplate(e.target.value)}
          />
        </div>
        <Button size="sm" onClick={() => configMut.mutate()} disabled={configMut.isPending}>
          Einstellungen speichern
        </Button>
      </Card>

      <div className="flex flex-wrap gap-2">
        {(["", "open", "in_progress", "resolved"] as const).map((s) => (
          <button
            key={s || "all"}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              statusFilter === s
                ? "bg-indigo-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {s === "" ? "Alle" : STATUS_LABELS[s]}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setHighOnly((v) => !v)}
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            highOnly ? "bg-orange-600 text-white" : "bg-slate-100 text-slate-600"
          }`}
        >
          Dringlichkeit ≥ Hoch
        </button>
        {tickets && (
          <span className="self-center text-xs text-slate-500">
            {tickets.open_count} offen
          </span>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2 pr-3 font-medium">Datum</th>
                <th className="pb-2 pr-3 font-medium">Mandant</th>
                <th className="pb-2 pr-3 font-medium">Dringlichkeit</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {tickets?.items.map((t) => (
                <tr
                  key={t.ticket_id}
                  className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 ${
                    selectedId === t.ticket_id ? "bg-indigo-50" : ""
                  }`}
                  onClick={() => openDetail(t)}
                >
                  <td className="py-2 pr-3 text-slate-600">
                    {new Date(t.created_at).toLocaleString("de-DE")}
                  </td>
                  <td className="py-2 pr-3">
                    <div className="font-medium">{t.account_display_name}</div>
                    <div className="text-xs text-slate-500">{t.created_by_email}</div>
                  </td>
                  <td className="py-2 pr-3">
                    <span
                      className={`rounded px-2 py-0.5 text-xs ${urgencyClass(t.urgency)}`}
                    >
                      {URGENCY_LABELS[t.urgency]}
                    </span>
                  </td>
                  <td className="py-2">{STATUS_LABELS[t.status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card className="space-y-4">
          {!selected ? (
            <p className="text-sm text-slate-500">Ticket auswählen für Details.</p>
          ) : (
            <>
              <div>
                <h3 className="font-medium text-slate-900">
                  {selected.subject || "Ohne Betreff"}
                </h3>
                <p className="text-xs text-slate-500">
                  {selected.account_display_name} · {selected.created_by_email}
                </p>
              </div>
              <p className="whitespace-pre-wrap text-sm text-slate-700">{selected.message}</p>
              <p className="text-xs text-slate-500">
                WhatsApp: {selected.whatsapp_notify_status}
                {selected.whatsapp_notify_error
                  ? ` — ${selected.whatsapp_notify_error}`
                  : ""}
              </p>
              <label className="block text-sm text-slate-700">
                Admin-Notiz
                <textarea
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  rows={3}
                  value={adminNote}
                  onChange={(e) => setAdminNote(e.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                {(["in_progress", "resolved", "closed"] as const).map((s) => (
                  <Button
                    key={s}
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      patchMut.mutate({
                        id: selected.ticket_id,
                        status: s,
                        note: adminNote,
                      })
                    }
                  >
                    {STATUS_LABELS[s]}
                  </Button>
                ))}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => retryMut.mutate(selected.ticket_id)}
                  disabled={retryMut.isPending}
                >
                  WhatsApp erneut
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
