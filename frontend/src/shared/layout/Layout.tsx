import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/shared/layout/Sidebar";
import { TopBar } from "@/shared/layout/TopBar";
import { MobileNavDrawer } from "@/shared/layout/MobileNavDrawer";

export function Layout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Close the mobile drawer when growing to desktop so the body-scroll lock
  // doesn't stick around on a viewport where the drawer is hidden.
  useEffect(() => {
    if (!mobileNavOpen) return;
    const onResize = () => {
      if (window.innerWidth >= 1024) setMobileNavOpen(false);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [mobileNavOpen]);

  return (
    <div className="flex min-h-screen" style={{ background: "#f1f5f9" }}>
      {/* Desktop sidebar — hidden below lg breakpoint */}
      <Sidebar />

      {/* Mobile slide-in drawer */}
      <MobileNavDrawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenuOpen={() => setMobileNavOpen(true)} />
        {/* Dot-grid background only visible in large empty spaces */}
        <main
          className="relative flex-1 overflow-auto p-4 md:p-6"
          style={{
            backgroundImage: "radial-gradient(circle, #cbd5e1 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        >
          <div className="relative mx-auto max-w-7xl animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
