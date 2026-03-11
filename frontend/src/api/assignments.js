import api from "./client";

export const assignmentsApi = {
  listForCampaign(campaignId) {
    return api.get(`/assignments/campaign/${campaignId}`);
  },
  create(campaignId, data) {
    return api.post(`/assignments/campaign/${campaignId}`, data);
  },
  complete(assignmentId) {
    return api.put(`/assignments/${assignmentId}/complete`);
  },
  getMyAssignments(status) {
    const params = status ? { status } : {};
    return api.get("/assignments/my", { params });
  },
};
