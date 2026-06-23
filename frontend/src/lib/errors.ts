import { AxiosError } from "axios";

/** Extracts a human-readable message from an unknown error (axios-aware). */
export function getErrorMessage(
  err: unknown,
  fallback = "Etwas ist schiefgelaufen. Bitte versuche es erneut."
): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as
      | { detail?: unknown; message?: unknown; error?: unknown }
      | undefined;
    const detail = data?.detail ?? data?.message ?? data?.error;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (err.code === "ERR_NETWORK") return "Server nicht erreichbar.";
    if (err.message) return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
