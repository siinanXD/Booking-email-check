import {
  MutationCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { AxiosError } from "axios";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import { getErrorMessage } from "@/lib/errors";
import { ErrorBoundary } from "@/shared/feedback/ErrorBoundary";
import { Toaster } from "@/shared/feedback/Toaster";
import { toast } from "@/shared/feedback/toastStore";
import "@/index.css";

function shouldRetry(failureCount: number, error: unknown): boolean {
  const status = error instanceof AxiosError ? error.response?.status : undefined;
  if (status && status >= 400 && status < 500) return false;
  return failureCount < 1;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 10_000, retry: shouldRetry },
  },
  // Surface every failed mutation globally unless it opts out via meta.
  mutationCache: new MutationCache({
    onError: (error, _vars, _ctx, mutation) => {
      if (mutation.meta?.skipGlobalError) return;
      toast.error(getErrorMessage(error));
    },
  }),
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster />
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>
);
