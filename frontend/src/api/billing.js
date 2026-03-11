import api from "./client";

export const billingApi = {
  getPlans: () => api.get("/billing/plans"),
  getStatus: () => api.get("/billing/status"),
  createCheckout: (priceId) => api.post("/billing/checkout", { price_id: priceId }),
  createPortal: () => api.post("/billing/portal"),
};
