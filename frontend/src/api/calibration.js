import api from "./client";

const calibrationAPI = {
  getOverview: (campaignId) => api.get(`/calibration/${campaignId}`),
  getCandidateDetail: (campaignId, candidateId) => api.get(`/calibration/${campaignId}/candidate/${candidateId}`),
};

export default calibrationAPI;
