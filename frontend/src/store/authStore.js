import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "../api/auth";

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      emailVerified: true, // default true for backwards compat
      isSuperuser: false,
      isLoading: true,

      setAuth(user, accessToken) {
        set({ user, accessToken, isAuthenticated: true, isSuperuser: user?.is_superuser || false, isLoading: false });
      },

      async login(email, password) {
        const res = await authApi.login({ email, password });
        const { access_token, user, email_verified } = res.data;
        set({
          user,
          accessToken: access_token,
          isAuthenticated: true,
          emailVerified: email_verified !== false,
          isSuperuser: user?.is_superuser || false,
          isLoading: false,
        });
        return res.data;
      },

      async signup(data) {
        const res = await authApi.signup(data);
        const { access_token, user, email_verified } = res.data;
        set({
          user,
          accessToken: access_token,
          isAuthenticated: true,
          emailVerified: email_verified !== false,
          isSuperuser: user?.is_superuser || false,
          isLoading: false,
        });
        return res.data;
      },

      async refresh() {
        try {
          const res = await authApi.refresh();
          const { access_token, user } = res.data;
          set({ user, accessToken: access_token, isAuthenticated: true, isSuperuser: user?.is_superuser || false, isLoading: false });
          return access_token;
        } catch {
          set({ user: null, accessToken: null, isAuthenticated: false, emailVerified: true, isSuperuser: false, isLoading: false });
          throw new Error("Session expired");
        }
      },

      setEmailVerified(verified) {
        set({ emailVerified: verified });
      },

      async logout() {
        try {
          await authApi.logout();
        } catch {
          // Logout endpoint may fail, but we still clear local state
        }
        set({ user: null, accessToken: null, isAuthenticated: false, emailVerified: true, isSuperuser: false, isLoading: false });
      },

      async initialize() {
        // If we have a persisted token, mark as not loading immediately
        // so the UI renders instantly. Then silently refresh in background.
        const { accessToken, user } = get();
        if (accessToken && user) {
          set({ isAuthenticated: true, isLoading: false });
          // Background refresh to validate session & get fresh token
          get().refresh().catch(() => {
            // Refresh failed — session expired, clear state
            set({ user: null, accessToken: null, isAuthenticated: false, emailVerified: true, isSuperuser: false, isLoading: false });
          });
        } else {
          // No persisted session — try cookie-based refresh
          try {
            await get().refresh();
          } catch {
            set({ isLoading: false });
          }
        }
      },
    }),
    {
      name: "corematch-auth",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
        emailVerified: state.emailVerified,
        isSuperuser: state.isSuperuser,
      }),
    }
  )
);
