import { useMutation, useQuery } from "@tanstack/react-query";
import { CreditCard } from "lucide-react";
import { fetchPlanCatalog, openBillingPortal, startCheckout } from "@/lib/api/billing";
import { formatLimit } from "@/lib/billing/display";
import type { SubscriptionResponse } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { toast } from "@/shared/feedback/toastStore";

const PAID_PLANS = new Set(["standard", "pro", "business"]);

export function SubscriptionSelfService({
  subscription,
}: {
  subscription: SubscriptionResponse;
}) {
  const { data: catalog } = useQuery({
    queryKey: ["billing-plans"],
    queryFn: fetchPlanCatalog,
    enabled: subscription.self_service,
  });

  const checkoutMut = useMutation({
    mutationFn: (planId: string) => startCheckout(planId),
    onError: () => toast.error("Checkout konnte nicht gestartet werden."),
  });

  const portalMut = useMutation({
    mutationFn: openBillingPortal,
    onError: () => toast.error("Kundenportal konnte nicht geöffnet werden."),
  });

  if (!subscription.self_service) {
    return (
      <p className="text-xs text-muted">
        Planänderungen erfolgen derzeit über den Support. Self-Service folgt nach
        Stripe-Aktivierung.
      </p>
    );
  }

  const showPortal =
    PAID_PLANS.has(subscription.plan_id) ||
    subscription.status === "past_due" ||
    subscription.status === "canceled";

  const upgradePlans =
    catalog?.items.filter(
      (plan) => plan.plan_id !== "trial" && plan.plan_id !== subscription.plan_id
    ) ?? [];

  return (
    <div className="space-y-3 border-t border-border pt-4">
      <p className="text-xs font-medium text-muted">
        Abo verwalten — Upgrade, Downgrade oder Kündigung über Stripe
      </p>

      {showPortal && (
        <Button
          variant="secondary"
          size="sm"
          loading={portalMut.isPending}
          onClick={() => portalMut.mutate()}
        >
          <CreditCard size={14} />
          Abo verwalten
        </Button>
      )}

      {!showPortal && upgradePlans.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-3">
          {upgradePlans.map((plan) => (
            <div
              key={plan.plan_id}
              className="flex flex-col justify-between rounded-xl border border-border bg-surface2 p-3"
            >
              <div>
                <p className="text-sm font-semibold text-ink">{plan.display_name}</p>
                <p className="mt-0.5 text-xs text-muted">
                  {plan.price_eur_monthly} €/Monat · {formatLimit(plan.monthly_mail_quota)}{" "}
                  Mails
                </p>
              </div>
              <Button
                className="mt-3 w-full"
                size="sm"
                loading={checkoutMut.isPending}
                onClick={() => checkoutMut.mutate(plan.plan_id)}
              >
                Upgraden
              </Button>
            </div>
          ))}
        </div>
      )}

      {showPortal && subscription.plan_id === "trial" && upgradePlans.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-3">
          {upgradePlans.map((plan) => (
            <Button
              key={plan.plan_id}
              variant="secondary"
              size="sm"
              loading={checkoutMut.isPending}
              onClick={() => checkoutMut.mutate(plan.plan_id)}
            >
              Zu {plan.display_name} wechseln
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
