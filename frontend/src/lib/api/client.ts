import axios, {
  AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/features/auth/authStore";

const baseURL = import.meta.env.VITE_API_URL ?? "";

export const apiClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function isAuthEndpoint(url: string): boolean {
  return (
    url.includes("/api/auth/login") ||
    url.includes("/api/auth/register") ||
    url.includes("/api/auth/refresh")
  );
}

// Single-flight refresh: concurrent 401s share one refresh request.
let refreshPromise: Promise<string | null> | null = null;

apiClient.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as
      | (InternalAxiosRequestConfig & { _retried?: boolean })
      | undefined;
    const status = err.response?.status;
    const url = original?.url ?? "";

    if (status !== 401 || !original || isAuthEndpoint(url) || original._retried) {
      if (status === 401 && original && !isAuthEndpoint(url)) {
        useAuthStore.getState().logout();
      }
      return Promise.reject(err);
    }

    original._retried = true;
    if (!refreshPromise) {
      refreshPromise = useAuthStore
        .getState()
        .refreshAccessToken()
        .finally(() => {
          refreshPromise = null;
        });
    }

    const newToken = await refreshPromise;
    if (!newToken) {
      useAuthStore.getState().logout();
      return Promise.reject(err);
    }

    original.headers.Authorization = `Bearer ${newToken}`;
    return apiClient(original);
  }
);
