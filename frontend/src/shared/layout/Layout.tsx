import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/shared/layout/Sidebar";
import { TopBar } from "@/shared/layout/TopBar";
import { MobileNavDrawer } from "@/shared/layout/MobileNavDrawer";
import { BottomTabBar } from "@/shared/layout/BottomTabBar";

export function Layout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Close the "more" drawer when growing to desktop so the body-scroll lock
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
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <MobileNavDrawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col bg-app">
        <TopBar />
        <main className="relative flex-1 overflow-auto p-4 md:p-[18px]">
          <div className="relative mx-auto max-w-7xl animate-fade-up">
            <Outlet />
          </div>
        </main>
        <BottomTabBar onMore={() => setMobileNavOpen(true)} />
      </div>
    </div>
  );
}
