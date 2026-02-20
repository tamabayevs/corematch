import api from "./client";

export const campaignsApi = {
  list(status) {
    const params = status ? { status } : {};
    return api.get("/campaigns", { params });
  },

  create(data) {
    return api.post("/campaigns", data);
  },

  get(id) {
    return api.get(`/campaigns/${id}`);
  },

  update(id, data) {
    return api.put(`/campaigns/${id}`, data);
  },

  inviteCandidate(campaignId, data) {
    return api.post(`/campaigns/${campaignId}/invite`, data);
  },
};
