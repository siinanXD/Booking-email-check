import { EmailListPage } from "@/pages/EmailListPage";

export function ChangesPage() {
  return (
    <EmailListPage
      title="Änderungen"
      subtitle="Buchungsänderungen"
      params={{ intent: "change", booking_related: true }}
    />
  );
}
