import { useQuery } from "@tanstack/react-query";
import { fetchAllAccounts } from "@/lib/api/admin";

/** Shared query for the full account list — one cache entry across admin pages. */
export function useAllAccounts() {
  return useQuery({
    queryKey: ["admin-accounts", "all"],
    queryFn: fetchAllAccounts,
  });
}
