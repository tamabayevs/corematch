import api from "./client";

export const demandApi = {
  stats() {
    return api.get("/demand/stats");
  },
};
