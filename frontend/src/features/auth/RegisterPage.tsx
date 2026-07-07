import { FormEvent, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { User, Mail, Phone, Lock, Building2, CheckCircle2, AlertCircle, Zap } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { RegisterFormFooter } from "@/features/auth/RegisterFormFooter";
import { useAuthStore } from "@/features/auth/authStore";
import { useAuthHydrated } from "@/features/auth/useAuthHydrated";

type AccountType = "private" | "business";

export function RegisterPage() {
  const hydrated = useAuthHydrated();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("private");
  const [companyName, setCompanyName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const register = useAuthStore((s) => s.register);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  if (isAuthenticated()) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (password !== passwordConfirm) {
      setError("Die Passwörter stimmen nicht überein.");
      return;
    }
    setLoading(true);
    try {
      const result = await register({
        email,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName,
        last_name: lastName,
        phone,
        account_type: accountType,
        company_name: accountType === "business" ? companyName : undefined,
      });
      setSuccess(result.message);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ?? "Registrierung fehlgeschlagen.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-4">
      {/* Background decoration */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-40 -top-40 h-96 w-96 rounded-full bg-brand/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-inquirytext/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-lg animate-fade-in">
        {/* Brand header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brandsoft ring-1 ring-brand/30">
            <Zap size={22} className="text-brandink" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Konto anlegen
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            Nach der Registrierung prüfen wir dein Konto manuell.
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-8 shadow-card-lg backdrop-blur-sm">
          {success ? (
            <div className="space-y-5 text-center">
              <div className="flex justify-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-okbg ring-1 ring-oktext/30">
                  <CheckCircle2 size={26} className="text-oktext" />
                </div>
              </div>
              <div>
                <p className="font-semibold text-ink">Registrierung erfolgreich!</p>
                <p className="mt-1 text-sm text-muted">{success}</p>
              </div>
              <Link to="/login">
                <Button className="w-full py-2.5">Zur Anmeldung</Button>
              </Link>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit} autoComplete="off">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-ink2">
                    Vorname
                  </label>
                  <div className="relative">
                    <User size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                    <Input
                      className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      required
                      placeholder="Max"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-ink2">
                    Nachname
                  </label>
                  <div className="relative">
                    <User size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                    <Input
                      className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      required
                      placeholder="Mustermann"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-ink2">
                  E-Mail-Adresse
                </label>
                <div className="relative">
                  <Mail size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                  <Input
                    id="register-email"
                    name="platform-register-email"
                    type="email"
                    className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="off"
                    placeholder="ihre@email.de"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-ink2">
                  Telefon
                </label>
                <div className="relative">
                  <Phone size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                  <Input
                    type="tel"
                    className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+49 170 1234567"
                    required
                  />
                </div>
              </div>

              {/* Account type */}
              <div className="space-y-2">
                <span className="block text-xs font-medium text-ink2">Nutzungsart</span>
                <div className="grid grid-cols-2 gap-2">
                  {(["private", "business"] as const).map((type) => (
                    <label
                      key={type}
                      className={`flex cursor-pointer items-center gap-2.5 rounded-lg border p-3 transition-all ${
                        accountType === type
                          ? "border-brand/50 bg-brandsoft text-ink"
                          : "border-border2 bg-surface2 text-muted hover:border-border hover:text-ink2"
                      }`}
                    >
                      <input
                        type="radio"
                        name="accountType"
                        className="accent-brand"
                        checked={accountType === type}
                        onChange={() => setAccountType(type)}
                      />
                      <span className="text-sm font-medium">
                        {type === "private" ? "Privat" : "Gewerblich"}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {accountType === "business" && (
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-ink2">
                    Firmenname
                  </label>
                  <div className="relative">
                    <Building2 size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                    <Input
                      className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      required
                      placeholder="Musterfirma GmbH"
                    />
                  </div>
                </div>
              )}

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-ink2">
                    Passwort
                  </label>
                  <div className="relative">
                    <Lock size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                    <Input
                      type="password"
                      className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      placeholder="Min. 8 Zeichen"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-ink2">
                    Passwort bestätigen
                  </label>
                  <div className="relative">
                    <Lock size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                    <Input
                      type="password"
                      className="pl-9 border-border2 bg-surface2 text-ink placeholder:text-faint focus:border-brand focus:ring-brand/20"
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      placeholder="Wiederholen"
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3"
                >
                  <AlertCircle size={14} className="mt-0.5 flex-shrink-0 text-red-400" />
                  <p className="text-xs text-red-300">{error}</p>
                </div>
              )}

              <Button type="submit" className="mt-1 w-full py-2.5" loading={loading}>
                {loading ? "Wird gesendet…" : "Registrieren"}
              </Button>

              <RegisterFormFooter />
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
