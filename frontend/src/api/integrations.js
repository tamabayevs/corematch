import api from "./client";

const integrationsAPI = {
  list: () => api.get("/integrations"),
  create: (data) => api.post("/integrations", data),
  update: (id, data) => api.put(`/integrations/${id}`, data),
  delete: (id) => api.delete(`/integrations/${id}`),
  test: (id) => api.post(`/integrations/${id}/test`),
  sync: (id) => api.post(`/integrations/${id}/sync`),
};

export default integrationsAPI;
