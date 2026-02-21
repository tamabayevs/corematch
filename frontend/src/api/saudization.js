import api from "./client";

const saudizationAPI = {
  dashboard: (params) => api.get("/saudization/dashboard", { params }),
  createQuota: (data) => api.post("/saudization/quotas", data),
  updateQuota: (id, data) => api.put(`/saudization/quotas/${id}`, data),
  deleteQuota: (id) => api.delete(`/saudization/quotas/${id}`),
  setNationality: (candidateId, nationality) => api.put(`/saudization/candidate/${candidateId}/nationality`, { nationality }),
};

export default saudizationAPI;
