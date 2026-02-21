import api from "./client";

export const talentPoolApi = {
  search(params) {
    return api.get("/talent-pool", { params });
  },
  listSavedSearches() {
    return api.get("/talent-pool/saved-searches");
  },
  saveSearch(data) {
    return api.post("/talent-pool/saved-searches", data);
  },
  deleteSavedSearch(id) {
    return api.delete(`/talent-pool/saved-searches/${id}`);
  },
};
