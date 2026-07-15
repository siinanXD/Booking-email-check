import { Link } from "react-router-dom";
import { Mail, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import type { MailConnectionResponse } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";

const mailStatusConfig = {
  connected: { color: "text-oktext", bg: "bg-okbg", ring: "ring-emerald-200/80", icon: CheckCircle2, label: "Verbunden" },
  error: { color: "text-dangertext", bg: "bg-dangerbg", ring: "ring-red-200/80", icon: XCircle, label: "Fehler" },
  default: { color: "text-ink2", bg: "bg-surface2", ring: "ring-slate-200/80", icon: AlertCircle, label: "Unbekannt" },
};

interface Props {
  mailData: MailConnectionResponse | undefined;
  testPending: boolean;
  onTest: () => void;
}

export function SettingsMailCard({ mailData, testPending, onTest }: Props) {
  const mailStatus = mailData?.status === "connected"
    ? mailStatusConfig.connected
    : mailData?.status === "error"
      ? mailStatusConfig.error
      : mailStatusConfig.default;
  const MailStatusIcon = mailStatus.icon;

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">Postfach</h3>
          <Link to="/onboarding?edit=1" className="text-xs font-medium text-brandink hover:text-brandink">
            Bearbeiten
          </Link>
        </div>
        {mailData ? (
          <>
            <div className="flex items-center gap-3 rounded-lg border border-border bg-surface2 px-4 py-3">
              <Mail size={16} className="flex-shrink-0 text-faint" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-ink">
                  {mailData.provider === "outlook" ? "Microsoft Outlook" : "IMAP"}
                  {mailData.email_address && (
                    <span className="font-normal text-muted"> · {mailData.email_address}</span>
                  )}
                </p>
                {mailData.last_sync_at && (
                  <p className="text-xs text-faint">
                    Letzter Sync: {new Date(mailData.last_sync_at).toLocaleString("de-DE")}
                  </p>
                )}
              </div>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${mailStatus.bg} ${mailStatus.color} ${mailStatus.ring}`}>
                <MailStatusIcon size={12} />
                {mailStatus.label}
              </span>
            </div>
            {mailData.last_error && (
              <p className="flex items-start gap-1.5 text-xs text-dangertext">
                <XCircle size={13} className="mt-0.5 flex-shrink-0" />
                {mailData.last_error}
              </p>
            )}
            <Button variant="secondary" size="sm" onClick={onTest} disabled={testPending}>
              {testPending ? "Teste…" : "Verbindung testen"}
            </Button>
          </>
        ) : (
          <p className="text-sm text-muted">
            Noch kein Postfach verbunden.{" "}
            <Link to="/onboarding?edit=1" className="text-brandink hover:underline">
              Jetzt einrichten
            </Link>
          </p>
        )}
      </div>
    </Card>
  );
}
