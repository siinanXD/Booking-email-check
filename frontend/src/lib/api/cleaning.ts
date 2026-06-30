import { apiClient } from "@/lib/api/client";

export interface CleaningPartner {
  partner_id: string;
  name: string;
  address?: string | null;
  contact_person?: string | null;
  phone?: string | null;
  locale: string;
  property_names: string[];
  active: boolean;
}

export interface CleaningTask {
  task_id: string;
  property_name?: string | null;
  room_number?: string | null;
  guest_name?: string | null;
  booking_number?: string | null;
  check_in?: string | null;
  check_out?: string | null;
  cleaning_date?: string | null;
  partner_id?: string | null;
  partner_name?: string | null;
  status: string;
  status_label: string;
  source_intent?: string | null;
  last_notification_status?: string | null;
  last_notification_error?: string | null;
  updated_at?: string | null;
}

export interface TaskFilters {
  status?: string;
  property_name?: string;
  from?: string;
  to?: string;
}

export interface PartnerPayload {
  name: string;
  address?: string | null;
  contact_person?: string | null;
  phone?: string | null;
  locale?: string;
  property_names?: string[];
  active?: boolean;
}

export async function fetchPartners(): Promise<{ items: CleaningPartner[] }> {
  const { data } = await apiClient.get("/api/cleaning/partners");
  return data;
}

export async function createPartner(
  payload: PartnerPayload
): Promise<CleaningPartner> {
  const { data } = await apiClient.post("/api/cleaning/partners", payload);
  return data;
}

export async function updatePartner(
  partnerId: string,
  payload: PartnerPayload
): Promise<CleaningPartner> {
  const { data } = await apiClient.put(
    `/api/cleaning/partners/${partnerId}`,
    payload
  );
  return data;
}

export async function deletePartner(partnerId: string): Promise<void> {
  await apiClient.delete(`/api/cleaning/partners/${partnerId}`);
}

function cleanFilters(filters: TaskFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.status) params.status = filters.status;
  if (filters.property_name) params.property_name = filters.property_name;
  if (filters.from) params.from = filters.from;
  if (filters.to) params.to = filters.to;
  return params;
}

export async function fetchTasks(
  filters: TaskFilters = {}
): Promise<{ items: CleaningTask[]; total: number }> {
  const { data } = await apiClient.get("/api/cleaning/tasks", {
    params: cleanFilters(filters),
  });
  return data;
}

export async function updateTask(
  taskId: string,
  payload: { status?: string; partner_id?: string | null }
): Promise<CleaningTask> {
  const { data } = await apiClient.patch(
    `/api/cleaning/tasks/${taskId}`,
    payload
  );
  return data;
}

export async function downloadTasksXlsx(filters: TaskFilters = {}): Promise<void> {
  const { data } = await apiClient.get("/api/cleaning/tasks/export", {
    params: cleanFilters(filters),
    responseType: "blob",
  });
  const blob = new Blob([data], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const stamp = new Date().toISOString().slice(0, 10);
  link.download = `Putzplan_${stamp}.xlsx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
