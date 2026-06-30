import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/shared/layout/Layout";
import { NotFoundPage } from "@/shared/components/NotFoundPage";
import { PlatformAdminRoute } from "@/routes/PlatformAdminRoute";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { TenantRoute } from "@/routes/TenantRoute";

const AdminAccountDetailPage = lazy(() =>
  import("@/features/admin/AdminAccountDetailPage").then((m) => ({ default: m.AdminAccountDetailPage }))
);
const AdminApprovalsPage = lazy(() =>
  import("@/features/admin/AdminApprovalsPage").then((m) => ({ default: m.AdminApprovalsPage }))
);
const AdminActivityPage = lazy(() =>
  import("@/features/admin/AdminActivityPage").then((m) => ({ default: m.AdminActivityPage }))
);
const AdminAuditPage = lazy(() =>
  import("@/features/admin/AdminAuditPage").then((m) => ({ default: m.AdminAuditPage }))
);
const AdminDiagnosticsPage = lazy(() =>
  import("@/features/admin/AdminDiagnosticsPage").then((m) => ({ default: m.AdminDiagnosticsPage }))
);
const AdminLayout = lazy(() =>
  import("@/features/admin/AdminLayout").then((m) => ({ default: m.AdminLayout }))
);
const AdminLlmConfigPage = lazy(() =>
  import("@/features/admin/AdminLlmConfigPage").then((m) => ({ default: m.AdminLlmConfigPage }))
);
const AdminWorkflowsPage = lazy(() =>
  import("@/features/admin/AdminWorkflowsPage").then((m) => ({ default: m.AdminWorkflowsPage }))
);
const AdminObservabilityPage = lazy(() =>
  import("@/features/admin/AdminObservabilityPage").then((m) => ({ default: m.AdminObservabilityPage }))
);
const AdminOverviewPage = lazy(() =>
  import("@/features/admin/AdminOverviewPage").then((m) => ({ default: m.AdminOverviewPage }))
);
const AdminPipelinePage = lazy(() =>
  import("@/features/admin/AdminPipelinePage").then((m) => ({ default: m.AdminPipelinePage }))
);
const AdminTicketsPage = lazy(() =>
  import("@/features/admin/AdminTicketsPage").then((m) => ({ default: m.AdminTicketsPage }))
);
const InboxPage = lazy(() =>
  import("@/features/emails/InboxPage").then((m) => ({ default: m.InboxPage }))
);
const DashboardPage = lazy(() =>
  import("@/features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage }))
);
const LandingPage = lazy(() =>
  import("@/features/marketing/LandingPage").then((m) => ({ default: m.LandingPage }))
);
const LoginPage = lazy(() =>
  import("@/features/auth/LoginPage").then((m) => ({ default: m.LoginPage }))
);
const OnboardingPage = lazy(() =>
  import("@/features/onboarding/OnboardingPage").then((m) => ({ default: m.OnboardingPage }))
);
const PropertiesPage = lazy(() =>
  import("@/features/properties/PropertiesPage").then((m) => ({ default: m.PropertiesPage }))
);
const PropertyProfilePage = lazy(() =>
  import("@/features/properties/PropertyProfilePage").then((m) => ({ default: m.PropertyProfilePage }))
);
const RegisterPage = lazy(() =>
  import("@/features/auth/RegisterPage").then((m) => ({ default: m.RegisterPage }))
);
const ReviewQueuePage = lazy(() =>
  import("@/features/review/ReviewQueuePage").then((m) => ({ default: m.ReviewQueuePage }))
);
const SettingsPage = lazy(() =>
  import("@/features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);
const SupportPage = lazy(() =>
  import("@/features/support/SupportPage").then((m) => ({ default: m.SupportPage }))
);
const PutzplanPage = lazy(() =>
  import("@/features/cleaning/PutzplanPage").then((m) => ({ default: m.PutzplanPage }))
);
const WorkflowRubrikPage = lazy(() =>
  import("@/features/workflows/WorkflowRubrikPage").then((m) => ({ default: m.WorkflowRubrikPage }))
);

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-sm text-faint">
      Lade…
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/welcome" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route element={<Layout />}>
              <Route element={<PlatformAdminRoute />}>
                <Route path="admin" element={<AdminLayout />}>
                  <Route index element={<Navigate to="overview" replace />} />
                  <Route path="overview" element={<AdminOverviewPage />} />
                  <Route path="accounts" element={<AdminApprovalsPage />} />
                  <Route path="accounts/:accountId" element={<AdminAccountDetailPage />} />
                  <Route path="activity" element={<AdminActivityPage />} />
                  <Route path="pipeline" element={<AdminPipelinePage />} />
                  <Route path="audit" element={<AdminAuditPage />} />
                  <Route path="diagnostics" element={<AdminDiagnosticsPage />} />
                  <Route path="observability" element={<AdminObservabilityPage />} />
                  <Route path="llm-config" element={<AdminLlmConfigPage />} />
                  <Route path="tickets" element={<AdminTicketsPage />} />
                  <Route path="workflows" element={<AdminWorkflowsPage />} />
                </Route>
                <Route
                  path="admin/approvals"
                  element={<Navigate to="/admin/accounts" replace />}
                />
              </Route>
              <Route element={<TenantRoute />}>
                <Route index element={<DashboardPage />} />
                <Route path="inbox" element={<InboxPage />} />
                <Route
                  path="bookings"
                  element={<Navigate to="/inbox?intent=new_booking" replace />}
                />
                <Route
                  path="cancellations"
                  element={<Navigate to="/inbox?intent=cancellation" replace />}
                />
                <Route
                  path="changes"
                  element={<Navigate to="/inbox?intent=change" replace />}
                />
                <Route
                  path="messages"
                  element={<Navigate to="/inbox?intent=guest_inquiry" replace />}
                />
                <Route path="properties" element={<PropertiesPage />} />
                <Route path="properties/:propertyId" element={<PropertyProfilePage />} />
                <Route path="cleaning" element={<PutzplanPage />} />
                <Route path="review" element={<ReviewQueuePage />} />
                <Route
                  path="ground-zero"
                  element={<Navigate to="/review?tab=grounding" replace />}
                />
                <Route
                  path="completed"
                  element={<Navigate to="/review?tab=completed" replace />}
                />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="support" element={<SupportPage />} />
                <Route path="rubrics/:slug" element={<WorkflowRubrikPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
