import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { SubscriptionSelfService } from "@/features/billing/SubscriptionSelfService";
import { UsageMeter } from "@/features/billing/UsageMeter";
import { UsageStatGrid } from "@/features/billing/UsageStatGrid";
import { fetchSubscription } from "@/lib/api/billing";
import { fetchMailConnection } from "@/lib/api/mail";
import {
  BILLING_SETTINGS_HASH,
  subscriptionStatusLabel,
} from "@/lib/billing/display";
import { Card } from "@/shared/ui/Card";
import { toast } from "@/shared/feedback/toastStore";

export function SubscriptionCard() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["billing-subscription"],
    queryFn: fetchSubscription,
  });
  const { data: mailConnection } = useQuery({
    queryKey: ["mail-connection"],
    queryFn: fetchMailConnection,
  });

  useEffect(() => {
    const checkout = searchParams.get("checkout");
    if (!checkout) return;
    if (checkout === "success") {
      toast.success("Zahlung erfolgreich — dein Abo wird aktualisiert.");
      void queryClient.invalidateQueries({ queryKey: ["billing-subscription"] });
    } else if (checkout === "cancel") {
      toast.info("Checkout abgebrochen.");
    }
    const next = new URLSearchParams(searchParams);
    next.delete("checkout");
    setSearchParams(next, { replace: true });
  }, [queryClient, searchParams, setSearchParams]);

  if (isLoading) {
    return (
      <Card id={BILLING_SETTINGS_HASH}>
        <p className="text-sm text-muted">Abo-Daten werden geladen…</p>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card id={BILLING_SETTINGS_HASH}>
        <p className="text-sm text-dangertext">
          Abo-Daten konnten nicht geladen werden.
        </p>
      </Card>
    );
  }

  const mailboxesUsed = mailConnection?.onboarding_completed ? 1 : 0;

  return (
    <Card id={BILLING_SETTINGS_HASH} className="scroll-mt-6">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-ink">Abo & Verbrauch</h3>
            <p className="mt-0.5 text-xs text-muted">
              Plan, Limits und Nutzung. Bezahlpläne werden sicher über Stripe
              abgewickelt.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-brandsoft px-2.5 py-0.5 text-xs font-semibold text-brandink">
              {data.plan_name}
            </span>
            <span className="rounded-full border border-border bg-surface2 px-2.5 py-0.5 text-xs font-medium text-muted">
              {subscriptionStatusLabel(data.status)}
            </span>
          </div>
        </div>

        <UsageStatGrid
          items={[
            {
              label: "Unterkünfte",
              used: data.properties_used,
              limit: data.properties_limit,
            },
            {
              label: "Mitarbeiter",
              used: data.users_used,
              limit: data.users_limit,
            },
            {
              label: "Postfächer",
              used: mailboxesUsed,
              limit: data.mailboxes_limit,
            },
          ]}
        />

        <UsageMeter
          label="Mails diesen Monat"
          used={data.mails_used}
          limit={data.mails_limit}
        />

        {data.period_end && (
          <p className="text-xs text-faint">
            Abrechnungsperiode bis{" "}
            {new Date(data.period_end).toLocaleDateString("de-DE")}
          </p>
        )}

        <SubscriptionSelfService subscription={data} />
      </div>
    </Card>
  );
}
