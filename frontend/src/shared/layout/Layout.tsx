import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { MobileNavDrawer } from "@/shared/layout/MobileNavDrawer";
import { Sidebar } from "@/shared/layout/Sidebar";
import { TopBar } from "@/shared/layout/TopBar";

export function Layout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen min-h-[100dvh]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-slate-900 focus:shadow-lg focus:outline focus:outline-2 focus:outline-indigo-600"
      >
        Zum Inhalt springen
      </a>
      <Sidebar />
      <MobileNavDrawer
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onOpenMenu={() => setMobileNavOpen(true)} menuOpen={mobileNavOpen} />
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 overflow-x-hidden overflow-y-auto p-4 sm:p-6 pb-[max(1rem,env(safe-area-inset-bottom))]"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
