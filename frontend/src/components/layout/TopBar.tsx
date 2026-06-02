import { Link } from "react-router-dom";
import { LogOut, User } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/Button";

export function TopBar() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <h1 className="text-lg font-semibold text-slate-800">AI Mail Platform</h1>
      <div className="flex items-center gap-4">
        <Link
          to="/settings"
          className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
          title="Einstellungen"
        >
          <User size={16} />
          {user?.email ?? "—"}
        </Link>
        <Button variant="ghost" onClick={logout} title="Abmelden">
          <LogOut size={18} />
        </Button>
      </div>
    </header>
  );
}
