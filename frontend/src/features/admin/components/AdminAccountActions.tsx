import { useState } from "react";
import { PauseCircle, PlayCircle, Trash2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  deleteAccount,
  setAccountExpiry,
  suspendAccount,
  unsuspendAccount,
} from "@/lib/api/admin";
import { Button } from "@/shared/ui/Button";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { toast } from "@/shared/feedback/toastStore";
import { formatTs } from "@/lib/format";

const EXPIRY_OPTIONS = [
  { label: "1 Woche", days: 7 },
  { label: "1 Monat", days: 30 },
  { label: "3 Monate", days: 90 },
  { label: "1 Jahr", days: 365 },
];

function addDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

type Pending =
  | { kind: "suspend" }
  | { kind: "unsuspend" }
  | { kind: "expiry"; iso: string | null; label: string }
  | { kind: "delete" }
  | null;

interface Props {
  accountId: string;
  isSuspended: boolean;
  expiresAt?: string | null;
}

export function AdminAccountActions({ accountId, isSuspended, expiresAt }: Props) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [pending, setPending] = useState<Pending>(null);
  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ["admin-account-detail", accountId] });

  const suspendMut = useMutation({
    mutationFn: () => suspendAccount(accountId),
    onSuccess: () => {
      invalidate();
      toast.success("Mandant gesperrt.");
    },
  });
  const unsuspendMut = useMutation({
    mutationFn: () => unsuspendAccount(accountId),
    onSuccess: () => {
      invalidate();
      toast.success("Mandant entsperrt.");
    },
  });
  const expiryMut = useMutation({
    mutationFn: (iso: string | null) => setAccountExpiry(accountId, iso),
    onSuccess: () => {
      invalidate();
      toast.success("Zugangsbegrenzung aktualisiert.");
    },
  });
  const deleteMut = useMutation({
    mutationFn: () => deleteAccount(accountId),
    onSuccess: () => {
      toast.success("Mandant gelöscht.");
      navigate("/admin/overview");
    },
  });

  const busy =
    suspendMut.isPending ||
    unsuspendMut.isPending ||
    expiryMut.isPending ||
    deleteMut.isPending;

  const runConfirm = () => {
    if (!pending) return;
    const done = () => setPending(null);
    if (pending.kind === "suspend") suspendMut.mutate(undefined, { onSettled: done });
    else if (pending.kind === "unsuspend") unsuspendMut.mutate(undefined, { onSettled: done });
    else if (pending.kind === "expiry") expiryMut.mutate(pending.iso, { onSettled: done });
    else if (pending.kind === "delete") deleteMut.mutate(undefined, { onSettled: done });
  };

  const dialog = pendingDialog(pending);

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {isSuspended ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPending({ kind: "unsuspend" })}
          >
            <PlayCircle size={14} aria-hidden /> Entsperren
          </Button>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPending({ kind: "suspend" })}
          >
            <PauseCircle size={14} aria-hidden /> Sperren
          </Button>
        )}

        <select
          value=""
          aria-label="Zugang begrenzen"
          onChange={(e) => {
            const v = e.target.value;
            if (!v) return;
            const opt = EXPIRY_OPTIONS.find((o) => String(o.days) === v);
            setPending({
              kind: "expiry",
              iso: v === "remove" ? null : addDays(Number(v)),
              label: v === "remove" ? "Begrenzung entfernen" : opt?.label ?? "",
            });
          }}
          className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-ink2 hover:bg-surface2"
        >
          <option value="" disabled>
            Zugang begrenzen…
          </option>
          {EXPIRY_OPTIONS.map((o) => (
            <option key={o.days} value={o.days}>
              {o.label}
            </option>
          ))}
          <option value="remove">Begrenzung entfernen</option>
        </select>

        {expiresAt && (
          <span className="flex items-center rounded-lg bg-warnbg px-3 py-1.5 text-xs text-warntext">
            Läuft ab: {formatTs(expiresAt)}
          </span>
        )}

        <Button
          variant="danger"
          size="sm"
          className="ml-auto"
          onClick={() => setPending({ kind: "delete" })}
        >
          <Trash2 size={14} aria-hidden /> Mandant löschen
        </Button>
      </div>

      <ConfirmDialog
        open={pending !== null}
        title={dialog.title}
        message={dialog.message}
        confirmLabel={dialog.confirmLabel}
        tone={dialog.tone}
        loading={busy}
        requirePhrase={pending?.kind === "delete" ? "LOESCHEN" : undefined}
        onConfirm={runConfirm}
        onCancel={() => !busy && setPending(null)}
      />
    </>
  );
}

function pendingDialog(pending: Pending): {
  title: string;
  message: string;
  confirmLabel: string;
  tone: "danger" | "primary";
} {
  switch (pending?.kind) {
    case "suspend":
      return {
        title: "Mandant sperren?",
        message: "Der Mandant verliert sofort den Zugang zur Plattform.",
        confirmLabel: "Sperren",
        tone: "danger",
      };
    case "unsuspend":
      return {
        title: "Mandant entsperren?",
        message: "Der Mandant erhält wieder vollen Zugang.",
        confirmLabel: "Entsperren",
        tone: "primary",
      };
    case "expiry":
      return {
        title: "Zugangsbegrenzung ändern?",
        message:
          pending.iso === null
            ? "Die Zugangsbegrenzung wird entfernt."
            : `Der Zugang wird auf „${pending.label}“ begrenzt.`,
        confirmLabel: "Übernehmen",
        tone: "primary",
      };
    case "delete":
      return {
        title: "Mandant endgültig löschen?",
        message: "Alle Daten dieses Mandanten werden unwiderruflich gelöscht.",
        confirmLabel: "Endgültig löschen",
        tone: "danger",
      };
    default:
      return { title: "", message: "", confirmLabel: "Bestätigen", tone: "primary" };
  }
}
