import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  fetchAdminAccountDetail,
  lockUser, resetUserPassword, deleteUser,
} from "@/lib/api/admin";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { ActivityBadge } from "@/features/admin/components/ActivityBadge";
import { AdminAccountActions } from "@/features/admin/components/AdminAccountActions";
import { DbCountsBarChart } from "@/features/admin/components/charts/DbCountsBarChart";
import { Card } from "@/shared/ui/Card";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { formatTs } from "@/lib/format";

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

export function AdminAccountDetailPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const qc = useQueryClient();
  const [resetPw, setResetPw] = useState<{ userId: string; value: string } | null>(null);
  const [confirmDelUser, setConfirmDelUser] = useState<{ id: string; email: string } | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-account-detail", accountId],
    queryFn: () => fetchAdminAccountDetail(accountId!),
    enabled: Boolean(accountId),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-account-detail", accountId] });

  const lockMut = useMutation({ mutationFn: ({ uid, locked }: { uid: string; locked: boolean }) => lockUser(accountId!, uid, locked), onSuccess: invalidate });
  const resetPwMut = useMutation({
    mutationFn: ({ uid, pw }: { uid: string; pw: string }) => resetUserPassword(accountId!, uid, pw),
    onSuccess: () => setResetPw(null),
  });
  const deleteUserMut = useMutation({
    mutationFn: (uid: string) => deleteUser(accountId!, uid),
    onSuccess: () => {
      invalidate();
      setConfirmDelUser(null);
    },
  });

  const isSuspended = data?.account.status === "suspended";

  if (!accountId) {
    return <p className="text-sm text-red-600">Keine Mandanten-ID.</p>;
  }

  if (isLoading) {
    return <p className="text-sm text-slate-500">Lade Mandanten-Details…</p>;
  }

  if (error || !data) {
    return (
      <Card>
        <p className="text-sm text-red-600">Mandant nicht gefunden.</p>
        <Link to="/admin/overview" className="mt-2 inline-block text-sm text-indigo-600">
          ← Zur Übersicht
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title={`Mandant: ${data.account.display_name}`}
        description="Detailansicht eines einzelnen Mandanten: Nutzung, Kosten, Postfach-Status und gespeicherte Daten in MongoDB. Die Aktivitäts-Ampel entspricht der Plattform-Übersicht."
        impact="Read-only — Änderungen an Verbindungen testest du unter Diagnose; LLM-Verhalten unter LLM-Konfiguration. Freischaltung erfolgt unter Mandanten."
      />

      <div className="flex items-center justify-between gap-4">
        <div>
          <Link
            to="/admin/overview"
            className="text-sm text-indigo-600 hover:underline"
          >
            ← Plattform-Übersicht
          </Link>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">
            {data.account.display_name}
          </h2>
          <p className="text-sm text-slate-500">{data.account.contact_email}</p>
        </div>
        <ActivityBadge status={data.activity_status} />
        <Link
          to={`/admin/workflows?account=${accountId}`}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Workflows verwalten
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-slate-500">Kosten (30 Tage)</p>
          <p className="mt-1 text-2xl font-semibold">{formatUsd(data.costs_30d_usd)}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Tokens (30 Tage)</p>
          <p className="mt-1 text-2xl font-semibold">
            {data.tokens_30d.toLocaleString("de-DE")}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Verarbeitete Mails (30 Tage)</p>
          <p className="mt-1 text-2xl font-semibold">{data.mails_processed_30d}</p>
        </Card>
      </div>

      {/* ── Admin Actions ─────────────────────────────────────────── */}
      <Card className="space-y-4">
        <h3 className="font-medium text-slate-900">Mandanten-Verwaltung</h3>
        <AdminAccountActions
          accountId={accountId}
          isSuspended={isSuspended}
          expiresAt={
            data.account && "expires_at" in data.account
              ? (data.account as { expires_at?: string | null }).expires_at
              : undefined
          }
        />
      </Card>

      <Card className="space-y-3">
        <h3 className="font-medium text-slate-900">Postfach</h3>
        {data.mail_connection ? (
          <>
            <p className="text-sm text-slate-600">
              {data.mail_connection.provider} · {data.mail_connection.email_address || "—"}{" "}
              · Status: {data.mail_connection.status}
            </p>
            <p className="text-xs text-slate-500">
              Letzter Sync: {formatTs(data.mail_connection.last_sync_at)}
            </p>
            {data.mail_connection.last_error && (
              <p className="text-xs text-red-600">{data.mail_connection.last_error}</p>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-500">Keine Postfach-Konfiguration.</p>
        )}
        <p className="text-xs text-slate-500">
          Letzte Mail: {formatTs(data.last_mail_received_at)}
        </p>
      </Card>

      <Card className="space-y-3">
        <h3 className="font-medium text-slate-900">Benutzer</h3>
        {data.users.length === 0 ? (
          <p className="text-sm text-slate-500">Keine Benutzer.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.users.map((u) => {
              const isLocked = (u as { is_locked?: boolean }).is_locked ?? false;
              return (
                <li key={u.id} className="flex flex-wrap items-center gap-2 py-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800">{u.email}</p>
                    <p className="text-xs text-slate-400">{u.role}{isLocked ? " · 🔒 gesperrt" : ""}</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {/* Lock / Unlock */}
                    <button
                      onClick={() => lockMut.mutate({ uid: u.id, locked: !isLocked })}
                      disabled={lockMut.isPending}
                      className={`rounded px-2 py-1 text-xs font-medium disabled:opacity-50 ${isLocked ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "bg-amber-50 text-amber-700 hover:bg-amber-100"}`}>
                      {isLocked ? "Entsperren" : "Sperren"}
                    </button>
                    {/* Reset password */}
                    {resetPw?.userId === u.id ? (
                      <div className="flex items-center gap-1">
                        <input autoFocus type="password" placeholder="Neues Passwort"
                          value={resetPw.value} onChange={(e) => setResetPw({ userId: u.id, value: e.target.value })}
                          className="w-36 rounded border border-slate-200 px-2 py-1 text-xs" />
                        <button onClick={() => resetPwMut.mutate({ uid: u.id, pw: resetPw.value })}
                          disabled={resetPwMut.isPending || resetPw.value.length < 8}
                          className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                          Setzen
                        </button>
                        <button onClick={() => setResetPw(null)} className="text-xs text-slate-400">✕</button>
                      </div>
                    ) : (
                      <button onClick={() => setResetPw({ userId: u.id, value: "" })}
                        className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200">
                        Passwort reset
                      </button>
                    )}
                    {/* Delete user */}
                    <button onClick={() => setConfirmDelUser({ id: u.id, email: u.email })}
                      disabled={deleteUserMut.isPending}
                      className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50">
                      Löschen
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <DbCountsBarChart counts={data.db_counts} />

      <Card className="space-y-3">
        <h3 className="font-medium text-slate-900">Datenbank-Counts (Tabelle)</h3>
        <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          {Object.entries(data.db_counts).map(([key, count]) => (
            <div key={key}>
              <dt className="text-slate-500">{key}</dt>
              <dd className="font-medium text-slate-900">{count}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {data.langfuse_session_url && (
        <Card>
          <h3 className="font-medium text-slate-900">Langfuse</h3>
          <p className="mt-1 text-xs text-slate-500">
            Session: {data.latest_correlation_id}
          </p>
          <a
            href={data.langfuse_session_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-sm text-indigo-600 hover:underline"
          >
            Trace in Langfuse öffnen →
          </a>
        </Card>
      )}

      <ConfirmDialog
        open={confirmDelUser !== null}
        title="Benutzer löschen?"
        message={
          confirmDelUser
            ? `Der Benutzer ${confirmDelUser.email} wird unwiderruflich gelöscht.`
            : ""
        }
        confirmLabel="Löschen"
        tone="danger"
        loading={deleteUserMut.isPending}
        onConfirm={() => confirmDelUser && deleteUserMut.mutate(confirmDelUser.id)}
        onCancel={() => !deleteUserMut.isPending && setConfirmDelUser(null)}
      />
    </div>
  );
}
