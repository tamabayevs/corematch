import api from "./client";

export const candidatesApi = {
  listByCampaign(campaignId, params = {}) {
    return api.get(`/candidates/campaign/${campaignId}`, { params });
  },

  get(id) {
    return api.get(`/candidates/${id}`);
  },

  updateDecision(id, decision, note) {
    return api.put(`/candidates/${id}/decision`, { decision, note });
  },

  erase(id) {
    return api.delete(`/candidates/${id}/erase`);
  },
};
