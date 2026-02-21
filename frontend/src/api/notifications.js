import api from "./client";

export const notificationsApi = {
  list(page = 1, unreadOnly = false) {
    return api.get("/notifications", { params: { page, unread_only: unreadOnly } });
  },
  markRead(id) {
    return api.put(`/notifications/${id}/read`);
  },
  markAllRead() {
    return api.put("/notifications/read-all");
  },
  getUnreadCount() {
    return api.get("/notifications/unread-count");
  },
};
