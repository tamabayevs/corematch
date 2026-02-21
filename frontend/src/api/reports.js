import api from "./client";

const reportsAPI = {
  executiveSummary: (params) => api.get("/reports/executive-summary", { params }),
  exportCSV: (params) => api.get("/reports/export/csv", { params, responseType: "blob" }),
  tierDistribution: (params) => api.get("/reports/tier-distribution", { params }),
};

export default reportsAPI;
