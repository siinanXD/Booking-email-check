import { Link } from "react-router-dom";
import {
  Mail,
  ListChecks,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  MessageCircle,
  Inbox,
  CheckCircle2,
} from "lucide-react";
import { Logo } from "@/shared/layout/Logo";
import { ThemeToggle } from "@/shared/theme/ThemeToggle";

const FEATURES = [
  {
    icon: Inbox,
    title: "Automatisch klassifiziert",
    body: "Buchung, Storno, Gastnachricht oder Änderung — jede Mail wird erkannt und eingeordnet.",
    tone: "bg-okbg text-oktext",
  },
  {
    icon: Sparkles,
    title: "Antworten als Entwurf",
    body: "Die KI entwirft passende Antworten mit zitierter Belegstelle. Versand erst nach Freigabe.",
    tone: "bg-brandsoft text-brandink",
  },
  {
    icon: MessageCircle,
    title: "WhatsApp-Hinweise",
    body: "Dein Team wird bei neuen Buchungen und Reinigungs-Aufgaben benachrichtigt.",
    tone: "bg-okbg text-whatsapp",
  },
  {
    icon: ShieldCheck,
    title: "DSGVO-konform",
    body: "Gast-Auskunft und Löschung, dokumentierte Einwilligungen, Audit-Log inklusive.",
    tone: "bg-infobg text-infotext",
  },
];

const STEPS = [
  { icon: Mail, label: "Mail erkannt" },
  { icon: ListChecks, label: "Klassifiziert" },
  { icon: Sparkles, label: "Antwort entworfen" },
  { icon: CheckCircle2, label: "Freigegeben" },
  { icon: MessageCircle, label: "Team benachrichtigt" },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      {/* Topbar */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <div className="flex items-center gap-2.5">
          <Logo size={34} />
          <span className="text-[15px] font-extrabold">Mail Assistant AI</span>
        </div>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <Link
            to="/login"
            className="rounded-xl px-3 py-2 text-[13px] font-semibold text-ink2 hover:text-ink"
          >
            Anmelden
          </Link>
          <Link
            to="/register"
            className="rounded-xl bg-brand-gradient px-4 py-2 text-[13px] font-bold text-white shadow-glow"
          >
            Kostenlos starten
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-5 pb-10 pt-10 text-center md:pt-16">
        <span className="inline-flex items-center gap-2 rounded-full bg-brandsoft px-3 py-1 text-[11px] font-bold uppercase tracking-[0.08em] text-brandink">
          <Sparkles size={13} /> KI für Gastgeber & Hotels
        </span>
        <h1 className="mx-auto mt-6 max-w-3xl text-[34px] font-extrabold leading-[1.1] tracking-tight md:text-[46px]">
          Buchungs-Mails lesen, einordnen und beantworten — automatisch.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-[15px] leading-relaxed text-muted md:text-[16px]">
          Mail Assistant AI liest deine Airbnb-, Booking.com- und Hotel-Mails,
          klassifiziert sie, entwirft Antworten und benachrichtigt dein Team per
          WhatsApp. Du gibst frei — gesendet wird nie ohne dich.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/register"
            className="inline-flex items-center gap-2 rounded-xl bg-brand-gradient px-6 py-3 text-[14px] font-bold text-white shadow-glow"
          >
            Kostenlos starten <ArrowRight size={16} />
          </Link>
          <Link
            to="/login"
            className="rounded-xl border border-border2 bg-surface px-6 py-3 text-[14px] font-semibold text-ink2 hover:bg-app"
          >
            Ich habe schon ein Konto
          </Link>
        </div>

        {/* Pipeline */}
        <div className="mx-auto mt-14 max-w-4xl rounded-2xl border border-border bg-surface p-5 shadow-card md:p-7">
          <div className="mb-5 flex items-center justify-center gap-2 text-[12px] font-bold text-ink2">
            <span className="h-2 w-2 animate-pulse-dot rounded-full bg-emerald-400" />
            So läuft jede eingehende Mail durch
          </div>
          <div className="flex flex-wrap items-stretch justify-center gap-2">
            {STEPS.map(({ icon: Icon, label }, i) => (
              <div
                key={label}
                className="flex min-w-[120px] flex-1 flex-col items-center gap-2 rounded-xl border border-border bg-app p-3.5"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brandsoft text-brandink">
                  <Icon size={17} />
                </span>
                <span className="text-[11.5px] font-bold text-ink">{label}</span>
                <span className="font-numeric text-[10px] text-faint">
                  Schritt {i + 1}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-5 py-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, body, tone }) => (
            <div
              key={title}
              className="rounded-2xl border border-border bg-surface p-5 shadow-card"
            >
              <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${tone}`}>
                <Icon size={19} />
              </span>
              <h3 className="mt-4 text-[14px] font-extrabold text-ink">{title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-5 py-10">
        <div className="relative overflow-hidden rounded-2xl bg-brand-gradient px-6 py-10 text-center shadow-card-lg">
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(rgba(255,255,255,.25) 1px, transparent 1px)",
              backgroundSize: "20px 20px",
            }}
          />
          <div className="relative">
            <h2 className="text-[24px] font-extrabold text-white md:text-[28px]">
              Spar dir den Posteingang-Stress.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-[14px] text-white/85">
              In wenigen Minuten Postfach verbinden und loslegen.
            </p>
            <Link
              to="/register"
              className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 text-[14px] font-bold text-brandink shadow-card-lg"
            >
              Jetzt kostenlos starten <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-6 text-[12px] text-faint sm:flex-row">
          <div className="flex items-center gap-2">
            <Logo size={24} />
            <span>© Mail Assistant AI</span>
          </div>
          <nav className="flex flex-wrap items-center gap-4">
            <Link to="/impressum" className="hover:text-ink2">
              Impressum
            </Link>
            <Link to="/datenschutz" className="hover:text-ink2">
              Datenschutz
            </Link>
          </nav>
          <span>Nur technisch notwendige Cookies. Kein Tracking.</span>
        </div>
      </footer>
    </div>
  );
}
