import api from "./client";

export const authApi = {
  signup(data) {
    return api.post("/auth/signup", data);
  },

  login(data) {
    return api.post("/auth/login", data);
  },

  refresh() {
    return api.post("/auth/refresh");
  },

  logout() {
    return api.post("/auth/logout");
  },

  getMe() {
    return api.get("/auth/me");
  },

  updateMe(data) {
    return api.put("/auth/me", data);
  },

  forgotPassword(email) {
    return api.post("/auth/forgot-password", { email });
  },

  resetPassword(token, password) {
    return api.post("/auth/reset-password", { token, password });
  },

  validateResetToken(token) {
    return api.get(`/auth/validate-reset-token?token=${encodeURIComponent(token)}`);
  },
};
