import { NavLink, Outlet } from "react-router-dom";
import { Shield } from "lucide-react";

const adminTabs = [
  { to: "/admin/overview", label: "Übersicht" },
  { to: "/admin/activity", label: "Aktivität" },
  { to: "/admin/pipeline", label: "Datenfluss" },
  { to: "/admin/accounts", label: "Mandanten" },
  { to: "/admin/audit", label: "Audit-Log" },
  { to: "/admin/diagnostics", label: "Diagnose" },
  { to: "/admin/observability", label: "Observability" },
  { to: "/admin/tickets", label: "Tickets" },
  { to: "/admin/llm-config", label: "LLM-Konfiguration" },
  { to: "/admin/workflows", label: "Workflows" },
];

export function AdminLayout() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-brandsoft text-brandink">
          <Shield size={18} />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-brand">
            Plattform-Administration
          </p>
          <h1 className="text-xl font-bold text-ink">Admin-Konsole</h1>
          <p className="mt-0.5 text-sm text-muted">
            Mandanten überwachen und konfigurieren — ohne eigenes Postfach.
          </p>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-border">
        <nav className="-mb-px flex gap-0 overflow-x-auto">
          {adminTabs.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={false}
              className={({ isActive }) =>
                `relative shrink-0 whitespace-nowrap px-4 py-2.5 text-sm font-medium transition-colors duration-150 ${
                  isActive
                    ? "text-brandink after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:rounded-t after:bg-brand"
                    : "text-muted hover:text-ink2"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <Outlet />
    </div>
  );
}
