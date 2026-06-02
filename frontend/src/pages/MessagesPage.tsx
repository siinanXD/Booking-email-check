import { EmailListPage } from "@/pages/EmailListPage";

export function MessagesPage() {
  return (
    <EmailListPage
      title="Nachrichten"
      subtitle="Gästeanfragen mit Buchungsbezug (bestehende Buchung oder Interesse)"
      params={{
        intent: "guest_inquiry",
        booking_related: true,
      }}
    />
  );
}
