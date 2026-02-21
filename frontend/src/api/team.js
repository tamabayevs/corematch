import api from "./client";

export const teamApi = {
  listMembers() {
    return api.get("/team/members");
  },
  invite(data) {
    return api.post("/team/invite", data);
  },
  updateRole(memberId, role) {
    return api.put(`/team/members/${memberId}`, { role });
  },
  removeMember(memberId) {
    return api.delete(`/team/members/${memberId}`);
  },
};
