import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { teamApi } from "../../api/team";

export default function TeamPage() {
  const { t } = useI18n();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "reviewer" });
  const [message, setMessage] = useState("");

  useEffect(() => { loadMembers(); }, []);

  const loadMembers = async () => {
    try {
      const { data } = await teamApi.listMembers();
      setMembers(data.members || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const handleInvite = async () => {
    try {
      await teamApi.invite(inviteForm);
      setShowInvite(false);
      setInviteForm({ email: "", role: "reviewer" });
      setMessage(t("team.inviteSent"));
      loadMembers();
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(e.response?.data?.error || "Failed to invite");
    }
  };

  const handleRoleChange = async (memberId, newRole) => {
    try {
      await teamApi.updateRole(memberId, newRole);
      loadMembers();
    } catch (e) { console.error(e); }
  };

  const handleRemove = async (memberId) => {
    if (!confirm(t("team.removeConfirm"))) return;
    try {
      await teamApi.removeMember(memberId);
      loadMembers();
    } catch (e) { console.error(e); }
  };

  const roles = ["admin", "recruiter", "reviewer", "viewer"];
  const roleBadgeColor = { admin: "bg-red-100 text-red-700", recruiter: "bg-primary-100 text-primary-700", reviewer: "bg-amber-100 text-amber-700", viewer: "bg-navy-100 text-navy-600" };

  if (loading) return <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("team.title")}</h1>
          <p className="text-navy-500 mt-1">{t("team.subtitle")}</p>
        </div>
        <button onClick={() => setShowInvite(true)} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          {t("team.invite")}
        </button>
      </div>

      {message && (
        <div className="mb-4 bg-primary-50 border border-primary-200 text-primary-700 px-4 py-2 rounded-lg text-sm">{message}</div>
      )}

      {members.length === 0 ? (
        <div className="text-center py-16 text-navy-400">
          <p className="text-lg font-medium">{t("team.noMembers")}</p>
          <p className="text-sm mt-1">{t("team.noMembersDesc")}</p>
        </div>
      ) : (
        <div className="bg-white border border-navy-200 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-navy-50 border-b border-navy-200">
              <tr>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("team.name")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("auth.email")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("team.role")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("candidate.status")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-100">
              {members.map((m) => (
                <tr key={m.id} className="hover:bg-navy-50">
                  <td className="px-4 py-3 text-sm font-medium text-navy-900">{m.full_name || "\u2014"}</td>
                  <td className="px-4 py-3 text-sm text-navy-600">{m.email}</td>
                  <td className="px-4 py-3">
                    <select value={m.role} onChange={e => handleRoleChange(m.id, e.target.value)}
                      className="text-xs border border-navy-200 rounded-lg px-2 py-1 bg-white">
                      {roles.map(r => <option key={r} value={r}>{t(`team.roles.${r}`)}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${m.status === "active" ? "bg-green-100 text-green-700" : "bg-navy-100 text-navy-500"}`}>
                      {m.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-end">
                    <button onClick={() => handleRemove(m.id)} className="text-xs text-red-500 hover:text-red-700">{t("common.delete")}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showInvite && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-navy-900 mb-4">{t("team.inviteMember")}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("auth.email")}</label>
                <input type="email" value={inviteForm.email} onChange={e => setInviteForm(p => ({ ...p, email: e.target.value }))}
                  className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm" placeholder="colleague@company.com" />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("team.role")}</label>
                <select value={inviteForm.role} onChange={e => setInviteForm(p => ({ ...p, role: e.target.value }))}
                  className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm">
                  {roles.map(r => <option key={r} value={r}>{t(`team.roles.${r}`)}</option>)}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowInvite(false)} className="px-4 py-2 text-sm text-navy-600 hover:bg-navy-100 rounded-lg">{t("common.cancel")}</button>
              <button onClick={handleInvite} className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium">{t("team.sendInvite")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
