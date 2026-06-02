import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/authStore";

vi.mock("@/api/auth", () => ({
  login: vi.fn(),
  fetchMe: vi.fn(),
  logoutApi: vi.fn().mockResolvedValue(undefined),
}));

describe("authStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
    });
  });

  it("reports unauthenticated without access token", () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);
  });

  it("reports authenticated when access token is set", () => {
    useAuthStore.setState({ accessToken: "test-token" });
    expect(useAuthStore.getState().isAuthenticated()).toBe(true);
  });

  it("clears session on logout", () => {
    useAuthStore.setState({
      accessToken: "test-token",
      refreshToken: "refresh",
      user: { id: "1", email: "a@b.de", role: "admin" },
    });
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
  });
});
