import api from "./client";

export const pipelineApi = {
  // Pipeline config
  getConfig: (campaignId) => api.get(`/pipeline/config/${campaignId}`),
  saveConfig: (campaignId, data) => api.post(`/pipeline/config/${campaignId}`, data),

  // Pipeline candidates
  getCandidates: (campaignId, params) =>
    api.get(`/pipeline/candidates/${campaignId}`, { params }),
  getCandidate: (candidateId) => api.get(`/pipeline/candidate/${candidateId}`),

  // HR decisions
  approve: (candidateId, data) =>
    api.post(`/pipeline/approve/${candidateId}`, data),
  reject: (candidateId, data) =>
    api.post(`/pipeline/reject/${candidateId}`, data),
  override: (candidateId, data) =>
    api.post(`/pipeline/override/${candidateId}`, data),
  rerun: (candidateId, stage) =>
    api.post(`/pipeline/rerun/${candidateId}/${stage}`),

  // Stats & providers
  getStats: (campaignId) => api.get(`/pipeline/stats/${campaignId}`),
  getProviders: () => api.get("/pipeline/providers"),
};
