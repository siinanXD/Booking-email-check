import { SidebarBrand, SidebarNav } from "@/shared/layout/sidebarNav";

export function Sidebar() {
  return (
    <aside className="hidden w-[230px] flex-none flex-col bg-rail-gradient px-3.5 py-2 lg:flex">
      <SidebarBrand />
      <div className="mx-1.5 mb-3 h-px bg-white/[0.07]" />
      <SidebarNav />
      <div className="mt-auto flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2">
        <span className="h-[7px] w-[7px] animate-pulse-dot rounded-full bg-emerald-400" />
        <span className="text-[11px] font-semibold text-emerald-300">System aktiv</span>
      </div>
    </aside>
  );
}
