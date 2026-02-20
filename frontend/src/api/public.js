import axios from "axios";

// Public API uses plain axios (no JWT interceptors needed)
const publicApi = axios.create({
  baseURL: "/api/public",
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
