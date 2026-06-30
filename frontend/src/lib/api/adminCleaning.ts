import { apiClient } from "@/lib/api/client";
import type { CleaningPartner, CleaningTask } from "@/lib/api/cleaning";

export interface AdminCleaningResponse {
  enabled: boolean;
  partners: CleaningPartner[];
  tasks: CleaningTask[];
}

export async function fetchAccountCleaning(
  accountId: string
): Promise<AdminCleaningResponse> {
  const { data } = await apiClient.get<AdminCleaningResponse>(
    `/api/admin/accounts/${accountId}/cleaning`
  );
  return data;
}
