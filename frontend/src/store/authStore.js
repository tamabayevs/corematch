import { create } from "zustand";
import { authApi } from "../api/auth";

export const useAuthStore = create((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,

  setAuth(user, accessToken) {
    set({ user, accessToken, isAuthenticated: true, isLoading: false });
  },

  async login(email, password) {
    const res = await authApi.login({ email, password });
    const { access_token, user } = res.data;
    set({ user, accessToken: access_token, isAuthenticated: true, isLoading: false });
    return res.data;
  },

  async signup(data) {
    const res = await authApi.signup(data);
    const { access_token, user } = res.data;
    set({ user, accessToken: access_token, isAuthenticated: true, isLoading: false });
    return res.data;
  },

  async refresh() {
    try {
      const res = await authApi.refresh();
      const { access_token, user } = res.data;
      set({ user, accessToken: access_token, isAuthenticated: true, isLoading: false });
      return access_token;
    } catch {
      set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false });
      throw new Error("Session expired");
    }
  },

  async logout() {
    try {
      await authApi.logout();
    } catch {
      // Logout endpoint may fail, but we still clear local state
    }
    set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false });
  },

  async initialize() {
    try {
      await get().refresh();
    } catch {
      set({ isLoading: false });
    }
  },
}));
