import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Logo } from "@/shared/layout/Logo";
import { ThemeToggle } from "@/shared/theme/ThemeToggle";

/** Rahmen für öffentliche Rechtstexte (Impressum, Datenschutz). */
export function LegalLayout({
  title,
  stand,
  children,
}: {
  title: string;
  stand?: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-5 py-4">
        <Link to="/welcome" className="flex items-center gap-2.5">
          <Logo size={30} />
          <span className="text-[15px] font-extrabold">Mail Assistant AI</span>
        </Link>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <Link
            to="/welcome"
            className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-[13px] font-semibold text-ink2 hover:text-ink"
          >
            <ArrowLeft size={14} /> Zurück
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 pb-16 pt-6">
        <h1 className="text-[26px] font-extrabold">{title}</h1>
        {stand ? (
          <p className="mt-1 text-[12px] text-faint">Stand: {stand}</p>
        ) : null}
        <div className="mt-6 space-y-6">{children}</div>
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-4 px-5 py-6 text-[12px] text-faint">
          <span>© Mail Assistant AI</span>
          <Link to="/impressum" className="hover:text-ink2">
            Impressum
          </Link>
          <Link to="/datenschutz" className="hover:text-ink2">
            Datenschutz
          </Link>
        </div>
      </footer>
    </div>
  );
}

/** Abschnitt mit Überschrift und Fließtext-Absätzen. */
export function LegalSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section>
      <h2 className="text-[16px] font-bold">{title}</h2>
      <div className="mt-2 space-y-2 text-[13.5px] leading-relaxed text-ink2">
        {children}
      </div>
    </section>
  );
}
