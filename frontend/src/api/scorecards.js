import api from "./client";

export const scorecardsApi = {
  listTemplates() {
    return api.get("/scorecards/templates");
  },
  createTemplate(data) {
    return api.post("/scorecards/templates", data);
  },
  updateTemplate(id, data) {
    return api.put(`/scorecards/templates/${id}`, data);
  },
  deleteTemplate(id) {
    return api.delete(`/scorecards/templates/${id}`);
  },
  submitEvaluation(candidateId, data) {
    return api.post(`/scorecards/evaluate/${candidateId}`, data);
  },
  getEvaluations(candidateId) {
    return api.get(`/scorecards/evaluate/${candidateId}`);
  },
};
