import type { PlatformSettingsResponse } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export interface SettingsWhatsAppCardProps {
  data: PlatformSettingsResponse | undefined;
  whatsappEnabled: boolean;
  onWhatsappEnabledChange: (value: boolean) => void;
  accessToken: string;
  onAccessTokenChange: (value: string) => void;
  phoneNumberId: string;
  onPhoneNumberIdChange: (value: string) => void;
  defaultRecipients: string;
  onDefaultRecipientsChange: (value: string) => void;
  testRecipient: string;
  onTestRecipientChange: (value: string) => void;
  testPending: boolean;
  onTest: () => void;
  testMessage: string | null;
}

export function SettingsWhatsAppCard({
  data,
  whatsappEnabled,
  onWhatsappEnabledChange,
  accessToken,
  onAccessTokenChange,
  phoneNumberId,
  onPhoneNumberIdChange,
  defaultRecipients,
  onDefaultRecipientsChange,
  testRecipient,
  onTestRecipientChange,
  testPending,
  onTest,
  testMessage,
}: SettingsWhatsAppCardProps) {
  return (
    <Card className="space-y-4">
      <h3 className="font-medium text-slate-800">WhatsApp (Meta Cloud API)</h3>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={whatsappEnabled}
          onChange={(e) => onWhatsappEnabledChange(e.target.checked)}
        />
        WhatsApp-Versand aktiv
      </label>
      <label className="block text-sm text-slate-600">
        Access Token
        {data?.whatsapp_access_token_set && (
          <span className="ml-2 text-xs text-green-700">(hinterlegt)</span>
        )}
        <Input
          className="mt-1"
          type="password"
          value={accessToken}
          onChange={(e) => onAccessTokenChange(e.target.value)}
          placeholder={
            data?.whatsapp_access_token_set
              ? "Leer lassen = unverändert"
              : "Meta Access Token"
          }
        />
      </label>
      <label className="block text-sm text-slate-600">
        Phone Number ID (nur Ziffern, aus Meta API Setup)
        <Input
          className="mt-1"
          value={phoneNumberId}
          onChange={(e) => onPhoneNumberIdChange(e.target.value)}
          placeholder="123456789012345"
        />
      </label>
      <label className="block text-sm text-slate-600">
        Standard-Empfänger (kommagetrennt, E.164)
        <Input
          className="mt-1"
          value={defaultRecipients}
          onChange={(e) => onDefaultRecipientsChange(e.target.value)}
          placeholder="+491701234567"
        />
      </label>
      <label className="block text-sm text-slate-600">
        Test-Empfänger (hello_world)
        <Input
          className="mt-1"
          value={testRecipient}
          onChange={(e) => onTestRecipientChange(e.target.value)}
          placeholder="+491701234567"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={onTest} disabled={testPending}>
          WhatsApp-Verbindung testen
        </Button>
      </div>
      {testMessage && (
        <p
          className={`text-sm ${testMessage.startsWith("Test erfolgreich") ? "text-green-700" : "text-red-600"}`}
        >
          {testMessage}
        </p>
      )}
    </Card>
  );
}
