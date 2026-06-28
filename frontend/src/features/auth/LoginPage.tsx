import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Mail, Lock, Zap, AlertCircle } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { useAuthStore } from "@/features/auth/authStore";
import { useAuthHydrated } from "@/features/auth/useAuthHydrated";
import { isAxiosError } from "axios";

export function LoginPage() {
  const hydrated = useAuthHydrated();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const loadUser = useAuthStore((s) => s.loadUser);

  useEffect(() => {
    if (!hydrated) return;
    void loadUser();
  }, [hydrated, loadUser]);

  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="text-sm text-muted">Lade…</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated()) {
    const isPlatformAdmin = useAuthStore.getState().isPlatformAdmin();
    return (
      <Navigate to={isPlatformAdmin ? "/admin/overview" : "/"} replace />
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      if (isAxiosError(err)) {
        if (!err.response) {
          setError(
            "Server nicht erreichbar. Backend starten und Seite neu laden."
          );
        } else if (err.response.data?.error) {
          setError(String(err.response.data.error));
        } else {
          setError("Anmeldung fehlgeschlagen. E-Mail oder Passwort prüfen.");
        }
      } else {
        setError("Anmeldung fehlgeschlagen. E-Mail oder Passwort prüfen.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-4">
      {/* Background decoration */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-96 w-96 rounded-full bg-brand/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-inquirytext/10 blur-3xl" />
        <div className="absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand/5 blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm animate-fade-in">
        {/* Brand header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brandsoft ring-1 ring-brand/30">
            <Zap size={22} className="text-brandink" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Mail Assistant AI
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            Melde dich mit deinem Konto an
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-border bg-surface p-8 shadow-card-lg backdrop-blur-sm">
          <form className="space-y-4" onSubmit={handleSubmit} autoComplete="off">
            <div className="space-y-1.5">
              <label
                className="block text-xs font-medium text-ink2"
                htmlFor="login-email"
              >
                E-Mail-Adresse
              </label>
              <div className="relative">
                <Mail
                  size={15}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
                />
                <input
                  id="login-email"
                  name="platform-login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  autoComplete="off"
                  placeholder="ihre@email.de"
                  className="w-full rounded-xl border border-border2 bg-surface2 py-2.5 pl-9 pr-3 text-sm text-ink placeholder:text-faint transition-all focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                className="block text-xs font-medium text-ink2"
                htmlFor="login-password"
              >
                Passwort
              </label>
              <div className="relative">
                <Lock
                  size={15}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
                />
                <input
                  id="login-password"
                  name="platform-login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-border2 bg-surface2 py-2.5 pl-9 pr-3 text-sm text-ink placeholder:text-faint transition-all focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                />
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border border-border bg-dangerbg p-3"
              >
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0 text-dangertext" />
                <p className="text-xs text-dangertext">{error}</p>
              </div>
            )}

            <Button type="submit" className="mt-2 w-full py-2.5" loading={loading}>
              {loading ? "Wird angemeldet…" : "Anmelden"}
            </Button>

            <p className="text-center text-xs text-muted">
              Noch kein Konto?{" "}
              <Link
                to="/register"
                className="font-medium text-brandink transition-colors hover:text-brand"
              >
                Registrieren
              </Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
