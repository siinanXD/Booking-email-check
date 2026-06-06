import { NavLink, Outlet } from "react-router-dom";

const adminTabs = [
  { to: "/admin/overview", label: "Übersicht", end: false },
  { to: "/admin/accounts", label: "Mandanten", end: false },
  { to: "/admin/diagnostics", label: "Diagnose", end: false },
  { to: "/admin/observability", label: "Observability", end: false },
  { to: "/admin/tickets", label: "Tickets", end: false },
  { to: "/admin/llm-config", label: "LLM-Konfiguration", end: false },
  { to: "/admin/workflows", label: "Workflows", end: false },
];

export function AdminLayout() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-indigo-600">
          Plattform-Administration
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">Admin-Konsole</h1>
        <p className="mt-1 text-sm text-slate-500">
          Mandanten überwachen und konfigurieren — ohne eigenes Postfach.
        </p>
      </div>
      <nav
        className="-mx-1 flex gap-2 overflow-x-auto border-b border-slate-200 pb-3 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        aria-label="Admin-Bereiche"
      >
        {adminTabs.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
