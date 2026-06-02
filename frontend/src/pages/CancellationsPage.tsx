import { EmailListPage } from "@/pages/EmailListPage";

export function CancellationsPage() {
  return (
    <EmailListPage
      title="Stornos"
      subtitle="Stornierungen"
      params={{ intent: "cancellation", booking_related: true }}
    />
  );
}
