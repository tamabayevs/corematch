import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { useNavigate } from "react-router-dom";
import { assignmentsApi } from "../../api/assignments";
import { campaignsApi } from "../../api/campaigns";

const STATUS_FILTERS = ["all", "pending", "completed"];

export default function AssignmentsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();

  const [myAssignments, setMyAssignments] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [campaignAssignments, setCampaignAssignments] = useState([]);
  const [campaignLoading, setCampaignLoading] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignForm, setAssignForm] = useState({ mode: "round_robin", reviewer_ids: [], count: 5 });
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadMyAssignments();
  }, [statusFilter]);

  const loadData = async () => {
    try {
      const [, campaignsRes] = await Promise.all([
        loadMyAssignments(),
        campaignsApi.list("active"),
      ]);
      setCampaigns(campaignsRes.data.campaigns || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const loadMyAssignments = async () => {
    try {
      const status = statusFilter === "all" ? undefined : statusFilter;
      const { data } = await assignmentsApi.getMyAssignments(status);
      setMyAssignments(data.assignments || []);
    } catch (e) { console.error(e); }
  };

  const loadCampaignAssignments = async (campaignId) => {
    setCampaignLoading(true);
    try {
      const { data } = await assignmentsApi.listForCampaign(campaignId);
      setCampaignAssignments(data.assignments || []);
    } catch (e) { console.error(e); } finally { setCampaignLoading(false); }
  };

  const handleSelectCampaign = (campaign) => {
    setSelectedCampaign(campaign);
    loadCampaignAssignments(campaign.id);
  };

  const handleComplete = async (assignmentId) => {
    try {
      await assignmentsApi.complete(assignmentId);
      loadMyAssignments();
      if (selectedCampaign) loadCampaignAssignments(selectedCampaign.id);
      setMessage(t("assignments.markedComplete"));
      setTimeout(() => setMessage(""), 3000);
    } catch (e) { console.error(e); }
  };

  const handleAssign = async () => {
    if (!selectedCampaign) return;
    try {
      await assignmentsApi.create(selectedCampaign.id, assignForm);
      setShowAssignModal(false);
      setAssignForm({ mode: "round_robin", reviewer_ids: [], count: 5 });
      loadCampaignAssignments(selectedCampaign.id);
      setMessage(t("assignments.assigned"));
      setTimeout(() => setMessage(""), 3000);
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">{t("assignments.title")}</h1>
        <p className="text-navy-500 mt-1">{t("assignments.subtitle")}</p>
      </div>

      {message && (
        <div className="bg-primary-50 border border-primary-200 text-primary-700 px-4 py-2 rounded-lg text-sm">{message}</div>
      )}

      {/* My Assignments Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-navy-900">{t("assignments.myAssignments")}</h2>
          <div className="flex gap-1 bg-navy-100 rounded-lg p-1">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  statusFilter === s ? "bg-white text-navy-900 shadow-sm" : "text-navy-500 hover:text-navy-700"
                }`}
              >
                {s === "all" ? t("common.all") : t(`assignments.status.${s}`)}
              </button>
            ))}
          </div>
        </div>

        {myAssignments.length === 0 ? (
          <div className="bg-white border border-navy-200 rounded-xl p-8 text-center text-navy-400">
            <svg className="w-10 h-10 mx-auto mb-2 text-navy-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
            <p className="font-medium">{t("assignments.noAssignments")}</p>
            <p className="text-sm mt-1">{t("assignments.noAssignmentsDesc")}</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {myAssignments.map((a) => (
              <div key={a.id} className="bg-white border border-navy-200 rounded-xl p-4 flex items-center gap-4 hover:shadow-sm transition-shadow">
                <div className={`w-2 h-2 rounded-full shrink-0 ${a.status === "completed" ? "bg-green-500" : "bg-accent-400"}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-navy-900 truncate">{a.candidate_name || a.candidate_email}</p>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      a.status === "completed" ? "bg-green-100 text-green-700" : "bg-accent-100 text-accent-700"
                    }`}>
                      {t(`assignments.status.${a.status}`)}
                    </span>
                  </div>
                  <p className="text-xs text-navy-500 mt-0.5">{a.campaign_name}</p>
                  {a.assigned_at && (
                    <p className="text-xs text-navy-400 mt-0.5">{t("assignments.assignedOn")} {new Date(a.assigned_at).toLocaleDateString()}</p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => navigate(`/dashboard/campaigns/${a.campaign_id}/candidates/${a.candidate_id}`)}
                    className="text-xs text-primary-600 hover:text-primary-700 font-medium px-3 py-1.5 rounded-lg hover:bg-primary-50"
                  >
                    {t("assignments.review")}
                  </button>
                  {a.status === "pending" && (
                    <button
                      onClick={() => handleComplete(a.id)}
                      className="text-xs text-green-600 hover:text-green-700 font-medium px-3 py-1.5 rounded-lg hover:bg-green-50"
                    >
                      {t("assignments.markComplete")}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Campaign Assignment Management */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-navy-900">{t("assignments.campaignManagement")}</h2>
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          {/* Campaign Selector */}
          <div className="bg-white border border-navy-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-navy-700 mb-3">{t("assignments.selectCampaign")}</h3>
            {campaigns.length === 0 ? (
              <p className="text-xs text-navy-400">{t("assignments.noCampaigns")}</p>
            ) : (
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {campaigns.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleSelectCampaign(c)}
                    className={`w-full text-start px-3 py-2 rounded-lg text-sm transition-colors ${
                      selectedCampaign?.id === c.id
                        ? "bg-primary-50 text-primary-700 font-medium border border-primary-200"
                        : "text-navy-700 hover:bg-navy-50"
                    }`}
                  >
                    <p className="font-medium truncate">{c.name}</p>
                    <p className="text-xs text-navy-400 truncate">{c.job_title}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Campaign Assignments */}
          <div className="lg:col-span-2">
            {!selectedCampaign ? (
              <div className="bg-white border border-navy-200 rounded-xl p-8 text-center text-navy-400">
                <p className="font-medium">{t("assignments.selectCampaignPrompt")}</p>
              </div>
            ) : campaignLoading ? (
              <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>
            ) : (
              <div className="bg-white border border-navy-200 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 bg-navy-50 border-b border-navy-200">
                  <div>
                    <h3 className="text-sm font-semibold text-navy-900">{selectedCampaign.name}</h3>
                    <p className="text-xs text-navy-500">{campaignAssignments.length} {t("assignments.totalAssignments")}</p>
                  </div>
                  <button
                    onClick={() => setShowAssignModal(true)}
                    className="bg-primary-600 hover:bg-primary-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
                  >
                    {t("assignments.assignReviewers")}
                  </button>
                </div>
                {campaignAssignments.length === 0 ? (
                  <div className="p-8 text-center text-navy-400 text-sm">{t("assignments.noAssignmentsForCampaign")}</div>
                ) : (
                  <table className="w-full">
                    <thead className="bg-navy-50/50">
                      <tr>
                        <th className="text-start px-4 py-2 text-xs font-semibold text-navy-500 uppercase">{t("assignments.reviewer")}</th>
                        <th className="text-start px-4 py-2 text-xs font-semibold text-navy-500 uppercase">{t("assignments.candidate")}</th>
                        <th className="text-start px-4 py-2 text-xs font-semibold text-navy-500 uppercase">{t("candidate.status")}</th>
                        <th className="text-start px-4 py-2 text-xs font-semibold text-navy-500 uppercase">{t("assignments.assignedDate")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-navy-100">
                      {campaignAssignments.map((a) => (
                        <tr key={a.id} className="hover:bg-navy-50">
                          <td className="px-4 py-2.5 text-sm text-navy-900">{a.reviewer_name || a.reviewer_email}</td>
                          <td className="px-4 py-2.5 text-sm text-navy-600">{a.candidate_name || a.candidate_email}</td>
                          <td className="px-4 py-2.5">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              a.status === "completed" ? "bg-green-100 text-green-700" : "bg-accent-100 text-accent-700"
                            }`}>
                              {t(`assignments.status.${a.status}`)}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-xs text-navy-400">
                            {a.assigned_at ? new Date(a.assigned_at).toLocaleDateString() : "\u2014"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Assign Reviewers Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-navy-900 mb-4">{t("assignments.assignReviewers")}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-2">{t("assignments.assignMode")}</label>
                <div className="flex gap-3">
                  <label className={`flex-1 flex items-center gap-2 border rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${
                    assignForm.mode === "round_robin" ? "border-primary-500 bg-primary-50" : "border-navy-200 hover:bg-navy-50"
                  }`}>
                    <input type="radio" name="mode" value="round_robin" checked={assignForm.mode === "round_robin"}
                      onChange={() => setAssignForm(p => ({ ...p, mode: "round_robin" }))}
                      className="text-primary-600" />
                    <div>
                      <p className="text-sm font-medium text-navy-900">{t("assignments.roundRobin")}</p>
                      <p className="text-xs text-navy-500">{t("assignments.roundRobinDesc")}</p>
                    </div>
                  </label>
                  <label className={`flex-1 flex items-center gap-2 border rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${
                    assignForm.mode === "manual" ? "border-primary-500 bg-primary-50" : "border-navy-200 hover:bg-navy-50"
                  }`}>
                    <input type="radio" name="mode" value="manual" checked={assignForm.mode === "manual"}
                      onChange={() => setAssignForm(p => ({ ...p, mode: "manual" }))}
                      className="text-primary-600" />
                    <div>
                      <p className="text-sm font-medium text-navy-900">{t("assignments.manual")}</p>
                      <p className="text-xs text-navy-500">{t("assignments.manualDesc")}</p>
                    </div>
                  </label>
                </div>
              </div>

              {assignForm.mode === "round_robin" && (
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("assignments.candidatesPerReviewer")}</label>
                  <input type="number" min="1" max="50" value={assignForm.count}
                    onChange={e => setAssignForm(p => ({ ...p, count: Number(e.target.value) }))}
                    className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              )}

              {assignForm.mode === "manual" && (
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("assignments.reviewerIds")}</label>
                  <textarea
                    value={assignForm.reviewer_ids.join(", ")}
                    onChange={e => setAssignForm(p => ({ ...p, reviewer_ids: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }))}
                    placeholder={t("assignments.reviewerIdsPlaceholder")}
                    rows={3}
                    className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm"
                  />
                  <p className="text-xs text-navy-400 mt-1">{t("assignments.reviewerIdsHint")}</p>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowAssignModal(false)} className="px-4 py-2 text-sm text-navy-600 hover:bg-navy-100 rounded-lg">{t("common.cancel")}</button>
              <button onClick={handleAssign} className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium">{t("assignments.assign")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
