import api from "./client";

export const brandingApi = {
  get() {
    return api.get("/branding");
  },
  update(data) {
    return api.put("/branding", data);
  },
  uploadLogo(file) {
    const formData = new FormData();
    formData.append("logo", file);
    return api.post("/branding/logo", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  removeLogo() {
    return api.delete("/branding/logo");
  },
};
