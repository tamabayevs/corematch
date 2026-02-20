import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { campaignsApi } from "../../api/campaigns";
import { candidatesApi } from "../../api/candidates";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import Modal from "../../components/ui/Modal";
import Spinner from "../../components/ui/Spinner";
import ScoreBadge from "../../components/ui/ScoreBadge";
import EmptyState from "../../components/ui/EmptyState";

const TIER_VARIANTS = {
  strong_proceed: "green",
  consider: "yellow",
  likely_pass: "red",
};

const STATUS_VARIANTS = {
  invited: "gray",
  started: "blue",
  submitted: "green",
};

const DECISION_VARIANTS = {
  shortlisted: "green",
  rejected: "red",
  hold: "yellow",
};

export default function CampaignDetailPage() {
  const { id } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({ full_name: "", email: "", phone: "" });
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState("");

  // Filters and sort
  const [sortBy, setSortBy] = useState("score");
  const [tierFilter, setTierFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    loadData();
  }, [id, sortBy, tierFilter, statusFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [campaignRes, candidatesRes] = await Promise.all([
        campaignsApi.get(id),
        candidatesApi.listByCampaign(id, {
          sort: sortBy,
          ...(tierFilter && { tier: tierFilter }),
          ...(statusFilter && { status: statusFilter }),
        }),
      ]);
      setCampaign(campaignRes.data.campaign);
      setCandidates(candidatesRes.data.candidates);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    setInviteError("");
    setInviteLoading(true);
    try {
      await campaignsApi.inviteCandidate(id, inviteForm);
      setShowInviteModal(false);
      setInviteForm({ full_name: "", email: "", phone: "" });
      loadData();
    } catch (err) {
      setInviteError(err.response?.data?.error || "Failed to send invitation");
    } finally {
      setInviteLoading(false);
    }
  };

  if (loading && !campaign) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (!campaign) return null;

  return (
    <div>
      {/* Campaign header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <button
            onClick={() => navigate("/dashboard")}
            className="text-sm text-gray-500 hover:text-gray-700 mb-2 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {t("common.back")}
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
          <p className="text-gray-500">{campaign.job_title}</p>
        </div>
        <Button onClick={() => setShowInviteModal(true)}>
          {t("campaign.inviteCandidate")}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="text-center !p-4">
          <p className="text-2xl font-bold text-gray-900">{campaign.candidate_count || 0}</p>
          <p className="text-sm text-gray-500">{t("dashboard.candidates")}</p>
        </Card>
        <Card className="text-center !p-4">
          <p className="text-2xl font-bold text-gray-900">{campaign.submitted_count || 0}</p>
          <p className="text-sm text-gray-500">{t("dashboard.submitted")}</p>
        </Card>
        <Card className="text-center !p-4">
          <p className="text-2xl font-bold text-gray-900">{campaign.questions?.length || 0}</p>
          <p className="text-sm text-gray-500">{t("campaign.questions")}</p>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="score">{t("candidate.score")}</option>
          <option value="name">{t("auth.fullName")}</option>
          <option value="date">{t("common.sort")}</option>
        </select>
        <select
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
        >
          <option value="">{t("candidate.tier")}: {t("common.all")}</option>
          <option value="strong_proceed">{t("candidate.strongProceed")}</option>
          <option value="consider">{t("candidate.consider")}</option>
          <option value="likely_pass">{t("candidate.likelyPass")}</option>
        </select>
        <select
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{t("candidate.status")}: {t("common.all")}</option>
          <option value="invited">{t("candidate.invited")}</option>
          <option value="started">{t("candidate.started")}</option>
          <option value="submitted">{t("candidate.submittedStatus")}</option>
        </select>
      </div>

      {/* Candidate list */}
      {candidates.length === 0 ? (
        <EmptyState
          title={t("candidate.noCandidates")}
          description={t("candidate.noCandidatesDesc")}
          actionLabel={t("campaign.inviteCandidate")}
          onAction={() => setShowInviteModal(true)}
        />
      ) : (
        <Card className="!p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-start px-4 py-3 text-sm font-medium text-gray-500">
                  {t("auth.fullName")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-gray-500">
                  {t("candidate.score")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-gray-500">
                  {t("candidate.tier")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-gray-500">
                  {t("candidate.status")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-gray-500">
                  {t("candidate.decision")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {candidates.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/dashboard/candidates/${c.id}`)}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{c.full_name}</p>
                      <p className="text-xs text-gray-500">{c.email}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {c.overall_score != null ? (
                      <ScoreBadge score={c.overall_score} tier={c.tier} />
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {c.tier ? (
                      <Badge variant={TIER_VARIANTS[c.tier]}>{t(`candidate.${c.tier === "strong_proceed" ? "strongProceed" : c.tier === "likely_pass" ? "likelyPass" : "consider"}`)}</Badge>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[c.status] || "gray"}>
                      {t(`candidate.${c.status === "submitted" ? "submittedStatus" : c.status}`)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {c.hr_decision ? (
                      <Badge variant={DECISION_VARIANTS[c.hr_decision]}>
                        {t(`candidate.${c.hr_decision}`)}
                      </Badge>
                    ) : (
                      <span className="text-sm text-gray-400">{t("candidate.noDecision")}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Invite Modal */}
      <Modal
        open={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        title={t("campaign.inviteCandidate")}
      >
        <form onSubmit={handleInvite} className="space-y-4">
          {inviteError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {inviteError}
            </div>
          )}
          <Input
            id="candidate_name"
            label={t("campaign.candidateName")}
            value={inviteForm.full_name}
            onChange={(e) => setInviteForm((prev) => ({ ...prev, full_name: e.target.value }))}
            required
          />
          <Input
            id="candidate_email"
            label={t("campaign.candidateEmail")}
            type="email"
            value={inviteForm.email}
            onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
            required
          />
          <Input
            id="candidate_phone"
            label={t("campaign.candidatePhone")}
            type="tel"
            value={inviteForm.phone}
            onChange={(e) => setInviteForm((prev) => ({ ...prev, phone: e.target.value }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setShowInviteModal(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" loading={inviteLoading}>
              {t("campaign.sendInvite")}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
