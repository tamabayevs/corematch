import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import api from "../../api/client";
import { campaignsApi } from "../../api/campaigns";
import { candidatesApi } from "../../api/candidates";
import { templatesApi } from "../../api/templates";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import Modal from "../../components/ui/Modal";
import Spinner from "../../components/ui/Spinner";
import ScoreBadge from "../../components/ui/ScoreBadge";
import EmptyState from "../../components/ui/EmptyState";

const TIER_VARIANTS = {
  strong_proceed: "teal",
  consider: "amber",
  likely_pass: "red",
};

const STATUS_VARIANTS = {
  invited: "gray",
  started: "blue",
  submitted: "teal",
};

const DECISION_VARIANTS = {
  shortlisted: "teal",
  rejected: "red",
  hold: "amber",
};

// ── CSV Parser ──────────────────────────────────────────────
function parseCSVText(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  const results = [];
  const headerPatterns = /^(name|full.?name|email|phone|candidate)/i;

  for (const line of lines) {
    // Skip header rows
    if (headerPatterns.test(line.trim())) continue;

    // Try comma, semicolon, then tab as delimiters
    let parts;
    if (line.includes(",")) parts = line.split(",").map((s) => s.trim());
    else if (line.includes(";")) parts = line.split(";").map((s) => s.trim());
    else if (line.includes("\t")) parts = line.split("\t").map((s) => s.trim());
    else continue;

    if (parts.length < 2) continue;

    const full_name = parts[0].replace(/^["']|["']$/g, "").trim();
    const email = parts[1].replace(/^["']|["']$/g, "").trim().toLowerCase();
    const phone = parts[2] ? parts[2].replace(/^["']|["']$/g, "").trim() : "";

    if (!full_name || !email) continue;

    const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    results.push({
      full_name,
      email,
      phone: phone || null,
      valid: isValidEmail && full_name.length > 0,
    });
  }

  // Deduplicate by email
  const seen = new Set();
  return results.filter((r) => {
    if (seen.has(r.email)) {
      r.valid = false;
      r.reason = "duplicate";
      return true;
    }
    seen.add(r.email);
    return true;
  });
}

export default function CampaignDetailPage() {
  const { id } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [campaign, setCampaign] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  // Single invite modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({ full_name: "", email: "", phone: "" });
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState("");

  // Bulk invite modal
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkStep, setBulkStep] = useState("input"); // input | preview | done
  const [bulkText, setBulkText] = useState("");
  const [bulkParsed, setBulkParsed] = useState([]);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  // Reminders
  const [reminderLoading, setReminderLoading] = useState(false);
  const [reminderResult, setReminderResult] = useState(null);

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

  // ── Single invite ─────────────────────────────────────────
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

  // ── Bulk invite ───────────────────────────────────────────
  const handleCSVUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setBulkText(ev.target.result);
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleBulkPreview = () => {
    const parsed = parseCSVText(bulkText);
    setBulkParsed(parsed);
    setBulkStep("preview");
  };

  const handleBulkSend = async () => {
    const validCandidates = bulkParsed
      .filter((c) => c.valid)
      .map(({ full_name, email, phone }) => ({ full_name, email, phone }));

    if (validCandidates.length === 0) return;

    setBulkLoading(true);
    try {
      const res = await campaignsApi.bulkInvite(id, validCandidates);
      setBulkResult(res.data);
      setBulkStep("done");
      loadData();
    } catch (err) {
      setBulkResult({ error: err.response?.data?.error || "Failed to send invitations" });
      setBulkStep("done");
    } finally {
      setBulkLoading(false);
    }
  };

  const resetBulkModal = () => {
    setShowBulkModal(false);
    setBulkStep("input");
    setBulkText("");
    setBulkParsed([]);
    setBulkResult(null);
  };

  // ── Reminders ─────────────────────────────────────────────
  const handleSendReminders = async () => {
    setReminderLoading(true);
    setReminderResult(null);
    try {
      const res = await campaignsApi.sendReminders(id);
      setReminderResult(res.data);
    } catch (err) {
      setReminderResult({ error: err.response?.data?.error || "Failed to send reminders" });
    } finally {
      setReminderLoading(false);
      setTimeout(() => setReminderResult(null), 5000);
    }
  };

  // ── Duplicate & Save as Template ────────────────────────
  const handleDuplicate = async () => {
    try {
      const res = await templatesApi.duplicateCampaign(id);
      navigate(`/dashboard/campaigns/${res.data.campaign.id}`);
    } catch {
      // Handle error silently
    }
  };

  const handleSaveAsTemplate = async () => {
    try {
      await templatesApi.saveFromCampaign(id);
      // Show brief success (reuse reminder toast pattern)
      setReminderResult({ message: t("template.savedAsTemplate") });
      setTimeout(() => setReminderResult(null), 3000);
    } catch {
      // Handle error silently
    }
  };

  // ── Export CSV ──────────────────────────────────────────────
  const handleExport = async () => {
    try {
      const res = await api.get(`/campaigns/${id}/export`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${campaign.name}-candidates.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch { }
  };

  // ── Copy Public Link ──────────────────────────────────────
  const [linkCopied, setLinkCopied] = useState(false);
  const handleCopyPublicLink = async () => {
    const publicUrl = `${window.location.origin}/apply/${id}`;
    try {
      await navigator.clipboard.writeText(publicUrl);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 3000);
    } catch {
      // Fallback for non-HTTPS contexts
      const textarea = document.createElement("textarea");
      textarea.value = publicUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 3000);
    }
  };

  // ── Derived counts ────────────────────────────────────────
  const invitedCount = candidates.filter((c) => c.status === "invited").length;

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
            className="text-sm text-navy-500 hover:text-navy-700 mb-2 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {t("common.back")}
          </button>
          <h1 className="text-2xl font-bold text-navy-900">{campaign.name}</h1>
          <p className="text-navy-500">{campaign.job_title}</p>
        </div>
        <div className="flex gap-2">
          {invitedCount > 0 && (
            <Button
              variant="secondary"
              onClick={handleSendReminders}
              loading={reminderLoading}
            >
              <svg className="w-4 h-4 me-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {t("bulkInvite.remind")} ({invitedCount})
            </Button>
          )}
          <Button variant="secondary" onClick={handleCopyPublicLink}>
            <svg className="w-4 h-4 me-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            {linkCopied ? t("common.copied") || "Copied!" : t("campaign.copyPublicLink") || "Copy Public Link"}
          </Button>
          <Button variant="secondary" onClick={handleExport}>
            <svg className="w-4 h-4 me-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {t("campaign.exportCSV")}
          </Button>
          <Button variant="secondary" onClick={handleSaveAsTemplate}>
            {t("template.saveAsTemplate")}
          </Button>
          <Button variant="secondary" onClick={handleDuplicate}>
            {t("template.duplicateCampaign")}
          </Button>
          <Button variant="secondary" onClick={() => setShowBulkModal(true)}>
            {t("bulkInvite.title")}
          </Button>
          <Button onClick={() => setShowInviteModal(true)}>
            {t("campaign.inviteCandidate")}
          </Button>
        </div>
      </div>

      {/* Reminder toast */}
      {reminderResult && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${reminderResult.error ? "bg-red-50 border border-red-200 text-red-700" : "bg-teal-50 border border-teal-200 text-teal-700"}`}>
          {reminderResult.error || reminderResult.message || t("bulkInvite.reminderSent", { count: reminderResult.reminded })}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="text-center !p-4">
          <p className="text-2xl font-bold text-navy-900">{campaign.candidate_count || 0}</p>
          <p className="text-sm text-navy-500">{t("dashboard.candidates")}</p>
        </Card>
        <Card className="text-center !p-4">
          <p className="text-2xl font-bold text-navy-900">{campaign.submitted_count || 0}</p>
          <p className="text-sm text-navy-500">{t("dashboard.submitted")}</p>
        </Card>
        <Card className="text-center !p-4">
          <p className="text-2xl font-bold text-navy-900">{campaign.questions?.length || 0}</p>
          <p className="text-sm text-navy-500">{t("campaign.questions")}</p>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select
          className="rounded-lg border border-navy-300 px-3 py-1.5 text-sm"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="score">{t("candidate.score")}</option>
          <option value="name">{t("auth.fullName")}</option>
          <option value="date">{t("common.sort")}</option>
        </select>
        <select
          className="rounded-lg border border-navy-300 px-3 py-1.5 text-sm"
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
        >
          <option value="">{t("candidate.tier")}: {t("common.all")}</option>
          <option value="strong_proceed">{t("candidate.strongProceed")}</option>
          <option value="consider">{t("candidate.consider")}</option>
          <option value="likely_pass">{t("candidate.likelyPass")}</option>
        </select>
        <select
          className="rounded-lg border border-navy-300 px-3 py-1.5 text-sm"
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
              <tr className="border-b border-navy-200 bg-navy-50">
                <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                  {t("auth.fullName")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                  {t("candidate.score")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                  {t("candidate.tier")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                  {t("candidate.status")}
                </th>
                <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                  {t("candidate.decision")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-200">
              {candidates.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-navy-50 cursor-pointer"
                  onClick={() => navigate(`/dashboard/candidates/${c.id}`)}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-navy-900">{c.full_name}</p>
                      <p className="text-xs text-navy-500">{c.email}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {c.overall_score != null ? (
                      <ScoreBadge score={c.overall_score} tier={c.tier} />
                    ) : (
                      <span className="text-sm text-navy-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {c.tier ? (
                      <Badge variant={TIER_VARIANTS[c.tier]}>{t(`candidate.${c.tier === "strong_proceed" ? "strongProceed" : c.tier === "likely_pass" ? "likelyPass" : "consider"}`)}</Badge>
                    ) : (
                      <span className="text-sm text-navy-400">-</span>
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
                      <span className="text-sm text-navy-400">{t("candidate.noDecision")}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* ── Single Invite Modal ───────────────────────────── */}
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

      {/* ── Bulk Invite Modal ─────────────────────────────── */}
      <Modal
        open={showBulkModal}
        onClose={resetBulkModal}
        title={t("bulkInvite.title")}
      >
        {bulkStep === "input" && (
          <div className="space-y-4">
            <p className="text-sm text-navy-500">{t("bulkInvite.description")}</p>

            {/* CSV Upload */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.txt"
              className="hidden"
              onChange={handleCSVUpload}
            />
            <Button
              variant="secondary"
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full"
            >
              <svg className="w-4 h-4 me-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {t("bulkInvite.uploadCSV")}
            </Button>

            {/* Paste area */}
            <div>
              <label className="block text-sm font-medium text-navy-700 mb-1">
                {t("bulkInvite.pasteData")}
              </label>
              <textarea
                className="w-full rounded-lg border border-navy-300 px-3 py-2 text-sm font-mono min-h-[120px] focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder={t("bulkInvite.placeholder")}
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
              />
              <p className="text-xs text-navy-400 mt-1">{t("bulkInvite.format")}</p>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={resetBulkModal}>
                {t("common.cancel")}
              </Button>
              <Button
                type="button"
                onClick={handleBulkPreview}
                disabled={!bulkText.trim()}
              >
                {t("bulkInvite.preview")}
              </Button>
            </div>
          </div>
        )}

        {bulkStep === "preview" && (
          <div className="space-y-4">
            {/* Summary badges */}
            <div className="flex gap-3">
              <Badge variant="teal">
                {t("bulkInvite.valid")}: {bulkParsed.filter((c) => c.valid).length}
              </Badge>
              <Badge variant="red">
                {t("bulkInvite.invalid")}: {bulkParsed.filter((c) => !c.valid).length}
              </Badge>
            </div>

            {/* Preview table */}
            <div className="max-h-64 overflow-y-auto border border-navy-200 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-navy-50 sticky top-0">
                  <tr>
                    <th className="text-start px-3 py-2 text-navy-500 font-medium">{t("auth.fullName")}</th>
                    <th className="text-start px-3 py-2 text-navy-500 font-medium">{t("auth.email")}</th>
                    <th className="text-start px-3 py-2 text-navy-500 font-medium">{t("candidate.status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-100">
                  {bulkParsed.map((c, i) => (
                    <tr key={i} className={c.valid ? "" : "bg-red-50"}>
                      <td className="px-3 py-2 text-navy-900">{c.full_name}</td>
                      <td className="px-3 py-2 text-navy-600">{c.email}</td>
                      <td className="px-3 py-2">
                        <Badge variant={c.valid ? "teal" : "red"}>
                          {c.valid ? t("bulkInvite.valid") : t("bulkInvite.invalid")}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setBulkStep("input")}>
                {t("common.back")}
              </Button>
              <Button
                type="button"
                onClick={handleBulkSend}
                loading={bulkLoading}
                disabled={bulkParsed.filter((c) => c.valid).length === 0}
              >
                {t("bulkInvite.send", { count: bulkParsed.filter((c) => c.valid).length })}
              </Button>
            </div>
          </div>
        )}

        {bulkStep === "done" && (
          <div className="space-y-4 text-center py-4">
            {bulkResult?.error ? (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {bulkResult.error}
              </div>
            ) : (
              <>
                <div className="w-12 h-12 bg-teal-100 rounded-full flex items-center justify-center mx-auto">
                  <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-navy-900 font-medium">
                  {t("bulkInvite.success", { count: bulkResult?.invited || 0 })}
                </p>
                {bulkResult?.skipped > 0 && (
                  <p className="text-sm text-navy-500">
                    {t("bulkInvite.skipped", { count: bulkResult.skipped })}
                  </p>
                )}
              </>
            )}
            <Button type="button" onClick={resetBulkModal} className="mt-4">
              {t("common.close")}
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}
