import { apiClient } from "@/lib/api/client";

export type NotificationKind =
  | "new_booking"
  | "whatsapp_sent"
  | "review_waiting"
  | "escalation";

export type NotificationItem = {
  id: string;
  kind: NotificationKind;
  title: string;
  detail?: string;
  created_at: string;
  read: boolean;
  href?: string;
};

export type NotificationsResponse = {
  items: NotificationItem[];
  unread: number;
};

export async function fetchNotifications(): Promise<NotificationsResponse> {
  const { data } = await apiClient.get<NotificationsResponse>("/api/notifications");
  return data;
}

export async function markNotificationsRead(): Promise<void> {
  await apiClient.post("/api/notifications/read-all");
}
