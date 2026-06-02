import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { BookingsPage } from "@/pages/BookingsPage";
import { CancellationsPage } from "@/pages/CancellationsPage";
import { ChangesPage } from "@/pages/ChangesPage";
import { CostsPage } from "@/pages/CostsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { MessagesPage } from "@/pages/MessagesPage";
import { PropertiesPage } from "@/pages/PropertiesPage";
import { ReviewQueuePage } from "@/pages/ReviewQueuePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="bookings" element={<BookingsPage />} />
            <Route path="cancellations" element={<CancellationsPage />} />
            <Route path="changes" element={<ChangesPage />} />
            <Route path="messages" element={<MessagesPage />} />
            <Route path="properties" element={<PropertiesPage />} />
            <Route path="review" element={<ReviewQueuePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="costs" element={<CostsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
