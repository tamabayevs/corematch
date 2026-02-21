import api from "./client";

export const brandingApi = {
  get() {
    return api.get("/branding");
  },
  update(data) {
    return api.put("/branding", data);
  },
};
