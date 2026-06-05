import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/shared/layout/Layout";
import { AdminAccountDetailPage } from "@/features/admin/AdminAccountDetailPage";
import { AdminApprovalsPage } from "@/features/admin/AdminApprovalsPage";
import { AdminDiagnosticsPage } from "@/features/admin/AdminDiagnosticsPage";
import { AdminLayout } from "@/features/admin/AdminLayout";
import { AdminLlmConfigPage } from "@/features/admin/AdminLlmConfigPage";
import { AdminWorkflowsPage } from "@/features/admin/AdminWorkflowsPage";
import { AdminObservabilityPage } from "@/features/admin/AdminObservabilityPage";
import { AdminOverviewPage } from "@/features/admin/AdminOverviewPage";
import { AdminTicketsPage } from "@/features/admin/AdminTicketsPage";
import { BookingsPage } from "@/features/emails/BookingsPage";
import { CancellationsPage } from "@/features/emails/CancellationsPage";
import { ChangesPage } from "@/features/emails/ChangesPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { MessagesPage } from "@/features/emails/MessagesPage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { PropertiesPage } from "@/features/properties/PropertiesPage";
import { PropertyProfilePage } from "@/features/properties/PropertyProfilePage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { CompletedPage } from "@/features/completed/CompletedPage";
import { GroundZeroPage } from "@/features/review/GroundZeroPage";
import { ReviewQueuePage } from "@/features/review/ReviewQueuePage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { SupportPage } from "@/features/support/SupportPage";
import { WorkflowRubrikPage } from "@/features/workflows/WorkflowRubrikPage";
import { PlatformAdminRoute } from "@/routes/PlatformAdminRoute";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { TenantRoute } from "@/routes/TenantRoute";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
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
                <Route path="diagnostics" element={<AdminDiagnosticsPage />} />
                <Route
                  path="observability"
                  element={<AdminObservabilityPage />}
                />
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
              <Route path="bookings" element={<BookingsPage />} />
              <Route path="cancellations" element={<CancellationsPage />} />
              <Route path="changes" element={<ChangesPage />} />
              <Route path="messages" element={<MessagesPage />} />
              <Route path="properties" element={<PropertiesPage />} />
              <Route path="properties/:propertyId" element={<PropertyProfilePage />} />
              <Route path="review" element={<ReviewQueuePage />} />
              <Route path="ground-zero" element={<GroundZeroPage />} />
              <Route path="completed" element={<CompletedPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="support" element={<SupportPage />} />
              <Route path="rubrics/:slug" element={<WorkflowRubrikPage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
