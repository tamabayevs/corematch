import api from "./client";

export const commentsApi = {
  list(candidateId) {
    return api.get(`/comments/${candidateId}`);
  },
  create(candidateId, data) {
    return api.post(`/comments/${candidateId}`, data);
  },
  update(commentId, content) {
    return api.put(`/comments/edit/${commentId}`, { content });
  },
  delete(commentId) {
    return api.delete(`/comments/edit/${commentId}`);
  },
};
