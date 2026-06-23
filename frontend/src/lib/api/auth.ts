import { apiClient } from "@/lib/api/client";
import type {
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
  UserResponse,
} from "@/lib/types/api";

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/api/auth/login", {
    email,
    password,
  });
  return data;
}

export async function register(
  payload: RegisterRequest
): Promise<RegisterResponse> {
  const { data } = await apiClient.post<RegisterResponse>(
    "/api/auth/register",
    payload
  );
  return data;
}

export async function refreshSession(
  refreshToken: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/api/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}

export async function fetchMe(accessToken: string): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>("/api/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function logoutApi(): Promise<void> {
  await apiClient.post("/api/auth/logout");
}
