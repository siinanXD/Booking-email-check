import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { BILLING_SETTINGS_PATH, formatLimit, usagePercent } from "@/lib/billing/display";
import type { SubscriptionResponse } from "@/lib/types/api";

export function MailQuotaBanner({
  subscription,
}: {
  subscription: SubscriptionResponse;
}) {
  if (subscription.mails_limit <= 0) return null;
  const mailQuotaPct = usagePercent(
    subscription.mails_used,
    subscription.mails_limit
  );
  if (mailQuotaPct < 80) return null;

  const urgent = mailQuotaPct >= 100;
  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border px-4 py-3 sm:flex-row sm:items-start sm:justify-between ${
        urgent ? "border-dangertext/30 bg-dangerbg" : "border-border bg-warnbg"
      }`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          size={16}
          className={`mt-0.5 flex-shrink-0 ${urgent ? "text-dangertext" : "text-warntext"}`}
        />
        <p className={`text-sm ${urgent ? "text-dangertext" : "text-warntext"}`}>
          {urgent ? (
            <>
              <span className="font-semibold">Mail-Kontingent aufgebraucht.</span>{" "}
              Neue Mails werden gespeichert, aber nicht mehr verarbeitet.
            </>
          ) : (
            <>
              <span className="font-semibold">{mailQuotaPct} % des Mail-Kontingents</span>{" "}
              verbraucht ({subscription.mails_used.toLocaleString("de-DE")} /{" "}
              {formatLimit(subscription.mails_limit)}).
            </>
          )}
        </p>
      </div>
      <Link
        to={BILLING_SETTINGS_PATH}
        className={`inline-flex shrink-0 items-center justify-center rounded-xl px-3 py-1.5 text-sm font-medium no-underline transition-colors ${
          urgent
            ? "bg-dangertext/10 text-dangertext hover:bg-dangertext/20"
            : "bg-warntext/10 text-warntext hover:bg-warntext/20"
        }`}
      >
        Abo ansehen
      </Link>
    </div>
  );
}
