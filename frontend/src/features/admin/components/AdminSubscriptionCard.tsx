import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  extendAccountTrial,
  fetchAdminAccountSubscription,
  fetchPlanCatalog,
  setAccountSubscription,
  setSubscriptionOverrides,
} from "@/lib/api/adminBilling";
import { UsageStatGrid } from "@/features/billing/UsageStatGrid";
import { subscriptionStatusLabel } from "@/lib/billing/display";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { toast } from "@/shared/feedback/toastStore";

const selectClass =
  "mt-1 block w-full min-w-[10rem] rounded-lg border border-border bg-surface px-2.5 py-1.5 text-sm text-ink";

export function AdminSubscriptionCard({ accountId }: { accountId: string }) {
  const { data: plans } = useQuery({
    queryKey: ["billing-plans"],
    queryFn: fetchPlanCatalog,
  });
  const { data: subscription, refetch } = useQuery({
    queryKey: ["admin-account-subscription", accountId],
    queryFn: () => fetchAdminAccountSubscription(accountId),
  });
  const [planId, setPlanId] = useState("trial");
  const [trialDays, setTrialDays] = useState("7");
  const [overrideMails, setOverrideMails] = useState("");
  const [overrideProps, setOverrideProps] = useState("");
  const [overrideUsers, setOverrideUsers] = useState("");

  useEffect(() => {
    if (!subscription) return;
    setPlanId(subscription.plan_id);
  }, [subscription?.plan_id]);

  const planMut = useMutation({
    mutationFn: () => setAccountSubscription(accountId, planId),
    onSuccess: () => {
      toast.success("Plan aktualisiert.");
      void refetch();
    },
  });
  const trialMut = useMutation({
    mutationFn: () => extendAccountTrial(accountId, Number(trialDays) || 7),
    onSuccess: () => {
      toast.success("Trial verlängert.");
      void refetch();
    },
  });
  const overrideMut = useMutation({
    mutationFn: () =>
      setSubscriptionOverrides(accountId, {
        override_max_mails: overrideMails.trim() ? Number(overrideMails) : null,
        override_max_properties: overrideProps.trim()
          ? Number(overrideProps)
          : null,
        override_max_users: overrideUsers.trim() ? Number(overrideUsers) : null,
      }),
    onSuccess: () => {
      toast.success("Overrides gespeichert.");
      setOverrideMails("");
      setOverrideProps("");
      setOverrideUsers("");
      void refetch();
    },
  });

  const sub = subscription ?? null;

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-ink">Abo-Verwaltung</h3>
      {sub ? (
        <div className="mb-4 space-y-3">
          <p className="text-sm text-muted">
            Status:{" "}
            <span className="font-medium text-ink">
              {subscriptionStatusLabel(sub.status)}
            </span>
          </p>
          <UsageStatGrid
            items={[
              {
                label: "Mails",
                used: sub.mails_used,
                limit: sub.mails_limit,
              },
              {
                label: "Unterkünfte",
                used: sub.properties_used,
                limit: sub.properties_limit,
              },
              {
                label: "Nutzer",
                used: sub.users_used,
                limit: sub.users_limit,
              },
            ]}
          />
        </div>
      ) : (
        <p className="mb-3 text-sm text-muted">
          Noch kein Abo — wird beim Freischalten angelegt.
        </p>
      )}

      <div className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="flex-1 text-xs text-muted">
            Plan
            <select
              className={selectClass}
              value={planId}
              onChange={(e) => setPlanId(e.target.value)}
            >
              {(plans?.items ?? []).map((p) => (
                <option key={p.plan_id} value={p.plan_id}>
                  {p.display_name}
                </option>
              ))}
              <option value="legacy">Legacy (intern)</option>
            </select>
          </label>
          <Button size="sm" onClick={() => planMut.mutate()} loading={planMut.isPending}>
            Plan ändern
          </Button>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="text-xs text-muted">
            Trial + Tage
            <Input
              className="mt-1 w-full sm:w-20"
              value={trialDays}
              onChange={(e) => setTrialDays(e.target.value)}
            />
          </label>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => trialMut.mutate()}
            loading={trialMut.isPending}
          >
            Trial verlängern
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-xs text-muted">
            Override Mails
            <Input
              value={overrideMails}
              onChange={(e) => setOverrideMails(e.target.value)}
              placeholder="Leer = Plan-Standard"
            />
          </label>
          <label className="text-xs text-muted">
            Override Unterkünfte
            <Input
              value={overrideProps}
              onChange={(e) => setOverrideProps(e.target.value)}
              placeholder="Leer = Plan-Standard"
            />
          </label>
          <label className="text-xs text-muted">
            Override Nutzer
            <Input
              value={overrideUsers}
              onChange={(e) => setOverrideUsers(e.target.value)}
              placeholder="Leer = Plan-Standard"
            />
          </label>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => overrideMut.mutate()}
          loading={overrideMut.isPending}
        >
          Overrides speichern
        </Button>
      </div>
    </Card>
  );
}
