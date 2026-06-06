import { Loader2, CheckCircle2, Search } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import type { MailConnectionResponse } from "@/lib/types/api";

type DiscoverState = "idle" | "loading" | "found" | "notfound";

interface Props {
  email: string;
  preset: string;
  imapUsername: string;
  imapPassword: string;
  imapHost: string;
  imapPort: number;
  discoverState: DiscoverState;
  discoverLabel: string;
  data: MailConnectionResponse | undefined;
  onEmailChange: (v: string) => void;
  onPresetChange: (v: string) => void;
  onImapUsernameChange: (v: string) => void;
  onImapPasswordChange: (v: string) => void;
  onImapHostChange: (v: string) => void;
  onImapPortChange: (v: number) => void;
  onDiscoverReset: () => void;
}

const cls = "border-white/10 bg-white/5 text-white placeholder:text-slate-600 focus:border-indigo-500/50 focus:ring-indigo-500/20";

const APP_PASSWORD_HINTS: Record<string, { text: string; url: string }> = {
  gmail:   { text: "Gmail erfordert ein App-Passwort (2-Faktor aktiv).", url: "https://myaccount.google.com/apppasswords" },
  yahoo:   { text: "Yahoo erfordert ein App-Passwort — kein normales Passwort.", url: "https://login.yahoo.com/account/security" },
  aol:     { text: "AOL erfordert ein App-Passwort — kein normales Passwort.", url: "https://login.aol.com/account/security" },
  icloud:  { text: "iCloud erfordert ein App-spezifisches Passwort.", url: "https://appleid.apple.com/" },
  gmx:     { text: "GMX: Einstellungen → E-Mail → POP3/IMAP → App-Passwort erstellen.", url: "https://www.gmx.net/service/sicherheit" },
  webde:   { text: "Web.de: Einstellungen → POP3/IMAP → App-Passwort erstellen.", url: "https://hilfe.web.de/pop-imap/" },
};

export function ImapConfigFields({
  email, preset, imapUsername, imapPassword, imapHost, imapPort,
  discoverState, discoverLabel, data,
  onEmailChange, onPresetChange, onImapUsernameChange, onImapPasswordChange,
  onImapHostChange, onImapPortChange, onDiscoverReset,
}: Props) {
  return (
    <>
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-slate-300">E-Mail-Adresse</label>
        <div className="relative">
          <Input type="email" value={email} onChange={(e) => { onEmailChange(e.target.value); onDiscoverReset(); }}
            required placeholder="ihre@email.de" className={`pr-9 ${cls}`} />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {discoverState === "loading" && <Loader2 size={14} className="animate-spin text-indigo-400" />}
            {discoverState === "found" && <CheckCircle2 size={14} className="text-emerald-400" />}
            {discoverState === "notfound" && <Search size={14} className="text-slate-500" />}
          </div>
        </div>
        {discoverState === "found" && (
          <p className="flex items-center gap-1.5 text-xs text-emerald-400">
            <CheckCircle2 size={11} />Anbieter erkannt: <span className="font-medium">{discoverLabel}</span>
          </p>
        )}
        {discoverState === "notfound" && (
          <p className="text-xs text-slate-500">Anbieter nicht erkannt — bitte manuell auswählen.</p>
        )}
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-slate-300">Anbieter</label>
        <select className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          value={preset}
          onChange={(e) => {
            onPresetChange(e.target.value);
            const item = data?.imap_presets.find((p) => p.id === e.target.value);
            if (item?.host) { onImapHostChange(item.host); onImapPortChange(item.port); }
            onDiscoverReset();
          }}>
          {(data?.imap_presets ?? []).map((p) => (
            <option key={p.id} value={p.id} className="bg-slate-800">{p.label}</option>
          ))}
        </select>
      </div>

      {preset === "custom" && (
        <div className="grid grid-cols-3 gap-2">
          <div className="col-span-2 space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">IMAP-Host</label>
            <Input value={imapHost} onChange={(e) => onImapHostChange(e.target.value)}
              required placeholder="imap.example.com" className={cls} />
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">Port</label>
            <Input type="number" value={imapPort}
              onChange={(e) => onImapPortChange(Number(e.target.value) || 993)} className={cls} />
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-slate-300">Benutzername</label>
        <Input value={imapUsername} onChange={(e) => onImapUsernameChange(e.target.value)}
          placeholder="Meist gleich wie E-Mail" className={cls} />
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-slate-300">App-Passwort</label>
        <Input type="password" value={imapPassword} onChange={(e) => onImapPasswordChange(e.target.value)}
          placeholder={data?.imap_password_set ? "Leer lassen = gespeichertes Passwort" : "App-Passwort des Anbieters"}
          className={cls} />
        {APP_PASSWORD_HINTS[preset] ? (
          <p className="flex items-start gap-1.5 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
            <span className="mt-px shrink-0">⚠️</span>
            <span>
              {APP_PASSWORD_HINTS[preset].text}{" "}
              <a href={APP_PASSWORD_HINTS[preset].url} target="_blank" rel="noreferrer"
                className="underline underline-offset-2 hover:text-amber-200">
                App-Passwort erstellen →
              </a>
            </span>
          </p>
        ) : (
          <p className="text-xs text-slate-500">
            Viele Anbieter erfordern ein separates App-Passwort (nicht das normale Konto-Passwort).
          </p>
        )}
      </div>
    </>
  );
}

export type { DiscoverState };

export function OutlookConfigFields({
  email, outlookMailbox, outlookAuthMode, oauthPending, oauthConnected, data,
  showAdvanced, onToggleAdvanced, onEmailChange, onOutlookMailboxChange,
  onOutlookAuthModeChange, onOutlookConnect,
}: {
  email: string; outlookMailbox: string; outlookAuthMode: string;
  oauthPending: boolean; oauthConnected: boolean; data: MailConnectionResponse | undefined;
  showAdvanced: boolean; onToggleAdvanced: () => void;
  onEmailChange: (v: string) => void; onOutlookMailboxChange: (v: string) => void;
  onOutlookAuthModeChange: (v: string) => void; onOutlookConnect: () => void;
}) {
  const useOAuth = outlookAuthMode === "oauth";
  return (
    <>
      {useOAuth && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
          <p className="text-sm text-slate-300">Melden Sie sich mit Ihrem Microsoft-Konto an.</p>
          {oauthConnected && (
            <p className="mt-2 flex items-center gap-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 size={14} />Verbunden als {data?.email_address || data?.outlook_mailbox}
            </p>
          )}
          <Button type="button" className="mt-3 w-full py-2.5" disabled={oauthPending} onClick={onOutlookConnect}>
            {oauthPending ? "Weiterleitung…" : oauthConnected ? "Erneut verbinden" : "Mit Microsoft anmelden"}
          </Button>
        </div>
      )}
      <button type="button" className="text-xs text-slate-500 transition-colors hover:text-slate-300" onClick={onToggleAdvanced}>
        {showAdvanced ? "Erweiterte Optionen ausblenden" : "Erweitert: Shared Mailbox / Device Code"}
      </button>
      {showAdvanced && (
        <>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">Auth-Modus</label>
            <select className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              value={outlookAuthMode} onChange={(e) => onOutlookAuthModeChange(e.target.value)}>
              <option value="oauth" className="bg-slate-800">OAuth (Browser-Anmeldung)</option>
              <option value="application" className="bg-slate-800">Application (Shared Mailbox)</option>
              <option value="delegated" className="bg-slate-800">Delegated (Device Code)</option>
            </select>
          </div>
          {outlookAuthMode !== "oauth" && (
            <>
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-slate-300">E-Mail-Adresse</label>
                <Input type="email" value={email} onChange={(e) => onEmailChange(e.target.value)}
                  required className={cls} />
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-slate-300">Mailbox (UPN)</label>
                <Input value={outlookMailbox} onChange={(e) => onOutlookMailboxChange(e.target.value)}
                  placeholder="vermieter@example.com" className={cls} />
              </div>
            </>
          )}
          <p className="text-xs text-slate-500">Azure Client ID und Secret werden serverseitig aus der .env gelesen.</p>
        </>
      )}
    </>
  );
}
