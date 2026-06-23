import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AxiosError } from "axios";
import {
  fetchMe,
  login as loginApi,
  logoutApi,
  refreshSession,
  register as registerApi,
} from "@/lib/api/auth";
import type { RegisterRequest, RegisterResponse, UserResponse } from "@/lib/types/api";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserResponse | null;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<RegisterResponse>;
  logout: () => void;
  loadUser: () => Promise<void>;
  refreshAccessToken: () => Promise<string | null>;
  isAuthenticated: () => boolean;
  isPlatformAdmin: () => boolean;
  isAccountAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: () =>
        Boolean(get().accessToken && get().user),
      isPlatformAdmin: () => get().user?.role === "platform_admin",
      isAccountAdmin: () => {
        const role = get().user?.role;
        return role === "owner" || role === "admin" || role === "platform_admin";
      },
      login: async (email, password) => {
        const tokens = await loginApi(email, password);
        try {
          const user = await fetchMe(tokens.access_token);
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            user,
          });
        } catch (err) {
          set({ accessToken: null, refreshToken: null, user: null });
          throw err;
        }
      },
      register: async (payload) => registerApi(payload),
      logout: () => {
        const token = get().accessToken;
        if (token) {
          logoutApi().catch(() => undefined);
        }
        set({ accessToken: null, refreshToken: null, user: null });
      },
      loadUser: async () => {
        const token = get().accessToken;
        if (!token) return;
        try {
          const user = await fetchMe(token);
          set({ user });
        } catch (err) {
          // Only drop the session on genuine auth failures — transient errors
          // (5xx, network) must not log the user out.
          const status =
            err instanceof AxiosError ? err.response?.status : undefined;
          if (status === 401 || status === 403) {
            get().logout();
          }
        }
      },
      refreshAccessToken: async () => {
        const refreshToken = get().refreshToken;
        if (!refreshToken) return null;
        try {
          const tokens = await refreshSession(refreshToken);
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
          });
          return tokens.access_token;
        } catch {
          return null;
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (s) => ({
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        user: s.user,
      }),
    }
  )
);
