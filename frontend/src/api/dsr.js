import api from "./client";

export const dsrApi = {
  list(params) {
    return api.get("/dsr", { params });
  },
  create(data) {
    return api.post("/dsr", data);
  },
  update(id, data) {
    return api.put(`/dsr/${id}`, data);
  },
  getStats() {
    return api.get("/dsr/stats");
  },
};
