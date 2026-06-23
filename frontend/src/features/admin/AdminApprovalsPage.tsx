import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  approveAccount,
  fetchAllAccounts,
  fetchPendingAccounts,
  rejectAccount,
} from "@/lib/api/admin";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";
import { toast } from "@/shared/feedback/toastStore";
import type { AccountListItem } from "@/lib/types/api";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { AccountStatusChart } from "@/features/admin/components/charts/AccountStatusChart";

function AccountRow({
  account,
  onApprove,
  onReject,
  busy,
}: {
  account: AccountListItem;
  onApprove: (id: string) => void;
  onReject: (id: string, reason: string) => void;
  busy: boolean;
}) {
  const [reason, setReason] = useState("");

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900">{account.display_name}</p>
          <p className="text-sm text-slate-600">{account.contact_email}</p>
          <p className="mt-1 text-xs text-slate-500">
            {account.account_type === "business" ? "Gewerblich" : "Privat"}
            {account.phone ? ` · ${account.phone}` : ""}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Registriert: {new Date(account.created_at).toLocaleString("de-DE")}
          </p>
        </div>
        <Badge
          label={account.status}
          tone={
            account.status === "active"
              ? "approved"
              : account.status === "pending"
                ? "pending"
                : "rejected"
          }
        />
      </div>

      {account.status === "pending" && (
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <label className="mb-1 block text-xs text-slate-500">
              Ablehnungsgrund (optional)
            </label>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Optional"
            />
          </div>
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => onReject(account.id, reason)}
          >
            Ablehnen
          </Button>
          <Button disabled={busy} onClick={() => onApprove(account.id)}>
            Freischalten
          </Button>
        </div>
      )}

      {account.rejection_reason && (
        <p className="mt-2 text-sm text-red-600">{account.rejection_reason}</p>
      )}
    </div>
  );
}

export function AdminApprovalsPage() {
  const queryClient = useQueryClient();
  const [showAll, setShowAll] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: showAll ? ["admin-accounts", "all"] : ["admin-accounts", "pending"],
    queryFn: showAll ? fetchAllAccounts : fetchPendingAccounts,
  });

  const mutation = useMutation({
    mutationFn: async ({
      action,
      accountId,
      reason,
    }: {
      action: "approve" | "reject";
      accountId: string;
      reason?: string;
    }) => {
      if (action === "approve") {
        await approveAccount(accountId);
      } else {
        await rejectAccount(accountId, reason);
      }
      return action;
    },
    onSuccess: (action) => {
      toast.success(
        action === "approve" ? "Mandant freigeschaltet." : "Mandant abgelehnt."
      );
      void queryClient.invalidateQueries({ queryKey: ["admin-accounts"] });
    },
  });

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Mandanten-Freischaltung"
        description="Neue Registrierungen erscheinen zuerst als „pending“. Nach Freischaltung kann der Mandant Postfach verbinden und Mails verarbeiten. Ablehnung ist endgültig und kann optional begründet werden."
        impact="Freischalten setzt den Account-Status auf „active“ — der Mandant erhält sofort Zugriff auf das Dashboard. Ablehnen sperrt den Zugang; der Grund wird dem Mandanten angezeigt."
      />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            {showAll ? "Alle Accounts" : "Ausstehende Freischaltungen"}
          </h2>
          <p className="text-sm text-slate-500">
            {showAll
              ? "Übersicht aller Mandanten inkl. Status"
              : "Neue Registrierungen prüfen und freischalten"}
          </p>
        </div>
        <Button
          variant="ghost"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Nur ausstehende" : "Alle Accounts"}
        </Button>
      </div>

      {showAll && data?.items && data.items.length > 0 && (
        <div className="max-w-md">
          <AccountStatusChart accounts={data.items} />
        </div>
      )}

      {isLoading && <p className="text-sm text-slate-500">Lade…</p>}
      {error && (
        <p className="text-sm text-red-600">
          Freischaltungen konnten nicht geladen werden.
        </p>
      )}

      <div className="space-y-3">
        {data?.items.map((account) => (
          <AccountRow
            key={account.id}
            account={account}
            busy={mutation.isPending}
            onApprove={(id) =>
              mutation.mutate({ action: "approve", accountId: id })
            }
            onReject={(id, reason) =>
              mutation.mutate({ action: "reject", accountId: id, reason })
            }
          />
        ))}
        {data && data.items.length === 0 && (
          <Card>
            <p className="text-sm text-slate-500">
              {showAll
                ? "Keine Accounts vorhanden."
                : "Keine ausstehenden Freischaltungen."}
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
