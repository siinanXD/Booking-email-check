import { SidebarBrand, SidebarNav } from "@/shared/layout/sidebarNav";

export function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 flex-col bg-slate-900 text-slate-200 lg:flex">
      <div className="border-b border-slate-700">
        <SidebarBrand />
      </div>
      <SidebarNav />
    </aside>
  );
}
