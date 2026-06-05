import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createSupportTicket, fetchSupportTickets } from "@/lib/api/support";
import type { SupportTicketUrgency } from "@/lib/types/api-support";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

const URGENCY_OPTIONS: { value: SupportTicketUrgency; label: string }[] = [
  { value: "low", label: "Niedrig" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "Hoch" },
  { value: "critical", label: "Kritisch" },
];

const STATUS_LABELS: Record<string, string> = {
  open: "Offen",
  in_progress: "In Bearbeitung",
  resolved: "Erledigt",
  closed: "Geschlossen",
};

function statusBadgeClass(status: string): string {
  if (status === "open") return "bg-amber-100 text-amber-800";
  if (status === "in_progress") return "bg-blue-100 text-blue-800";
  if (status === "resolved") return "bg-emerald-100 text-emerald-800";
  return "bg-slate-100 text-slate-700";
}

export function SupportPage() {
  const queryClient = useQueryClient();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [urgency, setUrgency] = useState<SupportTicketUrgency>("normal");
  const [successId, setSuccessId] = useState<string | null>(null);

  const { data: tickets } = useQuery({
    queryKey: ["support-tickets"],
    queryFn: () => fetchSupportTickets(),
  });

  const createMut = useMutation({
    mutationFn: () =>
      createSupportTicket({
        subject: subject.trim() || undefined,
        message: message.trim(),
        urgency,
      }),
    onSuccess: (ticket) => {
      setSuccessId(ticket.ticket_id);
      setSubject("");
      setMessage("");
      setUrgency("normal");
      queryClient.invalidateQueries({ queryKey: ["support-tickets"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Support</h1>
        <p className="mt-1 text-sm text-slate-500">
          Nachricht an den Plattform-Betreiber — bei technischen Fragen oder
          Problemen mit deinem Konto.
        </p>
      </div>

      <Card className="space-y-4">
        <h2 className="text-lg font-medium text-slate-900">Neues Ticket</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm text-slate-700">
            Dringlichkeit
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={urgency}
              onChange={(e) => setUrgency(e.target.value as SupportTicketUrgency)}
            >
              {URGENCY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-slate-700">
            Betreff (optional)
            <Input
              className="mt-1"
              value={subject}
              maxLength={120}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Kurztitel"
            />
          </label>
        </div>
        <label className="block text-sm text-slate-700">
          Nachricht
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            rows={5}
            maxLength={4000}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Beschreibe dein Anliegen…"
          />
          <span className="text-xs text-slate-400">{message.length}/4000</span>
        </label>
        {successId && (
          <p className="text-sm text-emerald-700">
            Ticket #{successId.slice(0, 8)} wurde erstellt.
          </p>
        )}
        {createMut.isError && (
          <p className="text-sm text-red-600">Ticket konnte nicht erstellt werden.</p>
        )}
        <Button
          disabled={!message.trim() || createMut.isPending}
          onClick={() => createMut.mutate()}
        >
          {createMut.isPending ? "Wird gesendet…" : "Ticket absenden"}
        </Button>
      </Card>

      <Card>
        <h2 className="mb-4 text-lg font-medium text-slate-900">Meine Anfragen</h2>
        {!tickets?.items.length ? (
          <p className="text-sm text-slate-500">Noch keine Tickets.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {tickets.items.map((t) => (
              <li key={t.ticket_id} className="py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(t.status)}`}
                  >
                    {STATUS_LABELS[t.status] ?? t.status}
                  </span>
                  <span className="text-xs text-slate-500">
                    {new Date(t.created_at).toLocaleString("de-DE")}
                  </span>
                </div>
                {t.subject && (
                  <p className="mt-1 font-medium text-slate-800">{t.subject}</p>
                )}
                <p className="mt-1 text-sm text-slate-600 line-clamp-2">{t.message}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
