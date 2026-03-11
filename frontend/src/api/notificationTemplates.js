import api from "./client";

const notificationTemplatesAPI = {
  list: (type) => api.get("/notification-templates", { params: type ? { type } : {} }),
  create: (data) => api.post("/notification-templates", data),
  update: (id, data) => api.put(`/notification-templates/${id}`, data),
  delete: (id) => api.delete(`/notification-templates/${id}`),
  preview: (id, values) => api.post(`/notification-templates/${id}/preview`, { values }),
};

export default notificationTemplatesAPI;
