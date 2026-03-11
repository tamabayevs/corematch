import api from "./client";

export const templatesApi = {
  list(isSystem) {
    const params = isSystem !== undefined ? { is_system: isSystem } : {};
    return api.get("/templates", { params });
  },
  create(data) {
    return api.post("/templates", data);
  },
  update(id, data) {
    return api.put(`/templates/${id}`, data);
  },
  delete(id) {
    return api.delete(`/templates/${id}`);
  },
  saveFromCampaign(campaignId) {
    return api.post(`/campaigns/${campaignId}/save-as-template`);
  },
  duplicateCampaign(campaignId) {
    return api.post(`/campaigns/${campaignId}/duplicate`);
  },
};
