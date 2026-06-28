import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/features/auth/authStore";
import { useAuthHydrated } from "@/features/auth/useAuthHydrated";
import { needsMailOnboarding } from "@/features/onboarding/mailOnboarding";

export function ProtectedRoute() {
  const hydrated = useAuthHydrated();
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const loadUser = useAuthStore((s) => s.loadUser);
  const location = useLocation();

  useEffect(() => {
    if (hydrated && accessToken && !user) {
      void loadUser();
    }
  }, [hydrated, accessToken, user, loadUser]);

  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg text-muted">
        Lade…
      </div>
    );
  }

  if (!accessToken) {
    // Gäste am Wurzelpfad sehen die öffentliche Landingpage, sonst Login.
    return <Navigate to={location.pathname === "/" ? "/welcome" : "/login"} replace />;
  }

  if (needsMailOnboarding(user) && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }

  return <Outlet />;
}
