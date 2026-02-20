import api from "./client";

export const dashboardApi = {
  summary() {
    return api.get("/dashboard/summary");
  },

  activity(limit = 10, offset = 0) {
    return api.get("/dashboard/activity", { params: { limit, offset } });
  },

  campaigns(status) {
    const params = status ? { status } : {};
    return api.get("/dashboard/campaigns", { params });
  },
};
