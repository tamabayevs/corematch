import axios from "axios";

// Public API uses plain axios (no JWT interceptors needed)
const PUBLIC_API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, "")}/api/public`
  : "/api/public";

const publicApi = axios.create({
  baseURL: PUBLIC_API_BASE,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

export const publicApiClient = {
  getInvite(token) {
    return publicApi.get(`/invite/${token}`);
  },

  recordConsent(token) {
    return publicApi.post(`/consent/${token}`);
  },

  uploadVideo(token, formData, onProgress) {
    return publicApi.post(`/video-upload/${token}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  },

  getStatus(token) {
    return publicApi.get(`/status/${token}`);
  },

  submitInterview(token, submitPartial = false) {
    return publicApi.post(`/submit/${token}`, { submit_partial: submitPartial });
  },
};
