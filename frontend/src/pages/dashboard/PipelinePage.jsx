import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { pipelineApi } from "../../api/pipeline";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Spinner from "../../components/ui/Spinner";
import EmptyState from "../../components/ui/EmptyState";
import AgentEvaluation from "../../components/pipeline/AgentEvaluation";
import PipelineProgress from "../../components/pipeline/PipelineProgress";

const STAGE_NAMES = {
  1: "cv_screening",
  2: "video_scoring",
  3: "deep_evaluation",
  4: "shortlist_ranking",
};

const STATUS_COLORS = {
  applied: "gray",
  screening: "blue",
  screen_complete: "amber",
  invited: "teal",
  started: "blue",
  submitted: "teal",
  video_scored: "amber",
  deep_eval: "blue",
  deep_complete: "amber",
  shortlisted: "teal",
  rejected: "red",
  on_hold: "amber",
};

export default function PipelinePage() {
  const { id: campaignId } = useParams();
  const navigate = useNavigate();
  const { t } = useI18n();

  const [candidates, setCandidates] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [candidateDetail, setCandidateDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    try {
      const [candRes, statsRes] = await Promise.all([
        pipelineApi.getCandidates(campaignId),
        pipelineApi.getStats(campaignId),
      ]);
      setCandidates(candRes.data.candidates || []);
      setStats(statsRes.data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load pipeline data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [campaignId]);

  const loadCandidateDetail = async (candidateId) => {
    setDetailLoading(true);
    try {
      const { data } = await pipelineApi.getCandidate(candidateId);
      setCandidateDetail(data);
      setSelectedCandidate(candidateId);
    } catch (err) {
      setError("Failed to load candidate details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleApprove = async (candidateId) => {
    setActionLoading(true);
    try {
      await pipelineApi.approve(candidateId, {});
      await loadData();
      if (selectedCandidate === candidateId) {
        await loadCandidateDetail(candidateId);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to approve");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (candidateId) => {
    setActionLoading(true);
    try {
      await pipelineApi.reject(candidateId, {});
      await loadData();
      if (selectedCandidate === candidateId) {
        await loadCandidateDetail(candidateId);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to reject");
    } finally {
      setActionLoading(false);
    }
  };

  const handleOverride = async (candidateId, reason) => {
    setActionLoading(true);
    try {
      const candidate = candidates.find((c) => c.id === candidateId);
      const latestEval = candidate?.evaluations?.[candidate.evaluations.length - 1];
      const newDecision = latestEval?.recommendation === "advance" ? "rejected" : "approved";
      await pipelineApi.override(candidateId, {
        new_decision: newDecision,
        reason,
      });
      await loadData();
      if (selectedCandidate === candidateId) {
        await loadCandidateDetail(candidateId);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to override");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <Spinner />;

  // Funnel stats
  const funnelStages = [
    { key: "applied", label: t("pipeline.funnel.applied"), count: stats?.applied || 0, color: "bg-navy-400" },
    { key: "screening", label: t("pipeline.funnel.screening"), count: stats?.screening || 0, color: "bg-blue-500" },
    { key: "screen_passed", label: t("pipeline.funnel.screened"), count: stats?.screen_complete || 0, color: "bg-amber-500" },
    { key: "interviewing", label: t("pipeline.funnel.interviewing"), count: (stats?.invited || 0) + (stats?.started || 0) + (stats?.submitted || 0), color: "bg-teal-500" },
    { key: "evaluated", label: t("pipeline.funnel.evaluated"), count: stats?.deep_complete || 0, color: "bg-purple-500" },
    { key: "shortlisted", label: t("pipeline.funnel.shortlisted"), count: stats?.shortlisted || 0, color: "bg-green-500" },
    { key: "rejected", label: t("pipeline.funnel.rejected"), count: stats?.rejected || 0, color: "bg-red-500" },
  ];

  const maxCount = Math.max(...funnelStages.map((s) => s.count), 1);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button
            onClick={() => navigate(`/dashboard/campaigns/${campaignId}`)}
            className="text-sm text-primary-600 hover:text-primary-700 mb-1 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {t("common.back")}
          </button>
          <h1 className="text-2xl font-bold text-navy-900">{t("pipeline.title")}</h1>
          <p className="text-sm text-navy-500">{t("pipeline.subtitle")}</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
          <button onClick={() => setError("")} className="ms-2 underline">dismiss</button>
        </div>
      )}

      {/* Pipeline Funnel */}
      <Card className="mb-6">
        <h2 className="text-sm font-semibold text-navy-800 mb-4">{t("pipeline.funnel.title")}</h2>
        <div className="space-y-2">
          {funnelStages.map((stage) => (
            <div key={stage.key} className="flex items-center gap-3">
              <span className="text-xs text-navy-500 w-24 text-end">{stage.label}</span>
              <div className="flex-1 bg-navy-100 rounded-full h-6 overflow-hidden">
                <div
                  className={`${stage.color} h-full rounded-full flex items-center justify-end pe-2 transition-all duration-500`}
                  style={{ width: `${Math.max((stage.count / maxCount) * 100, stage.count > 0 ? 8 : 0)}%` }}
                >
                  {stage.count > 0 && (
                    <span className="text-xs font-medium text-white">{stage.count}</span>
                  )}
                </div>
              </div>
              {stage.count === 0 && (
                <span className="text-xs text-navy-400">0</span>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Candidate list + detail panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Candidate list */}
        <div className="lg:col-span-2">
          <Card>
            <h2 className="text-sm font-semibold text-navy-800 mb-4">
              {t("pipeline.candidates")} ({candidates.length})
            </h2>
            {candidates.length === 0 ? (
              <EmptyState
                title={t("pipeline.noCandidates")}
                description={t("pipeline.noCandidatesDesc")}
              />
            ) : (
              <div className="divide-y divide-navy-100">
                {candidates.map((c) => {
                  const latestEval = c.evaluations?.[c.evaluations?.length - 1];
                  const isSelected = selectedCandidate === c.id;

                  return (
                    <div
                      key={c.id}
                      onClick={() => loadCandidateDetail(c.id)}
                      className={`py-3 px-3 -mx-3 cursor-pointer hover:bg-navy-50 rounded-lg transition-colors ${
                        isSelected ? "bg-primary-50 ring-1 ring-primary-200" : ""
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-navy-900">{c.full_name}</span>
                          <Badge variant={STATUS_COLORS[c.status] || "gray"} size="sm">
                            {t(`pipeline.status.${c.status}`) || c.status}
                          </Badge>
                        </div>
                        {latestEval?.overall_score != null && (
                          <span className={`text-sm font-bold ${
                            latestEval.overall_score >= 70 ? "text-green-600" :
                            latestEval.overall_score >= 40 ? "text-amber-600" : "text-red-600"
                          }`}>
                            {Math.round(latestEval.overall_score)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-navy-500">
                        <span>{c.email}</span>
                        {c.pipeline_stage > 0 && (
                          <span>Stage {c.pipeline_stage}</span>
                        )}
                        {latestEval?.recommendation && (
                          <span className={`font-medium ${
                            latestEval.recommendation === "advance" ? "text-green-600" :
                            latestEval.recommendation === "reject" ? "text-red-600" : "text-amber-600"
                          }`}>
                            {t(`pipeline.recommendation.${latestEval.recommendation}`)}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Detail panel */}
        <div>
          {detailLoading ? (
            <Card><Spinner /></Card>
          ) : candidateDetail ? (
            <div className="space-y-4">
              {/* Candidate info */}
              <Card>
                <h3 className="text-sm font-semibold text-navy-800 mb-2">
                  {candidateDetail.candidate?.full_name}
                </h3>
                <div className="space-y-1 text-xs text-navy-500">
                  <p>{candidateDetail.candidate?.email}</p>
                  {candidateDetail.candidate?.phone && <p>{candidateDetail.candidate.phone}</p>}
                  {candidateDetail.candidate?.linkedin_url && (
                    <a
                      href={candidateDetail.candidate.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline"
                    >
                      LinkedIn Profile
                    </a>
                  )}
                </div>
                <div className="mt-3">
                  <PipelineProgress
                    currentStage={candidateDetail.candidate?.pipeline_stage || 0}
                    evaluations={candidateDetail.evaluations || []}
                  />
                </div>
              </Card>

              {/* CV document */}
              {candidateDetail.documents?.length > 0 && (
                <Card>
                  <h3 className="text-xs font-semibold text-navy-800 mb-2">{t("pipeline.cvDocument")}</h3>
                  {candidateDetail.documents.map((doc) => (
                    <div key={doc.id} className="text-xs text-navy-600">
                      <p className="font-medium">{doc.original_filename}</p>
                      <p className="text-navy-400">
                        {(doc.file_size_bytes / 1024).toFixed(0)} KB &middot; {doc.extraction_status}
                      </p>
                    </div>
                  ))}
                </Card>
              )}

              {/* Evaluations */}
              {(candidateDetail.evaluations || []).map((eval_) => (
                <AgentEvaluation
                  key={eval_.id}
                  evaluation={eval_}
                  onApprove={
                    !eval_.hr_decision && eval_.recommendation
                      ? () => handleApprove(candidateDetail.candidate.id)
                      : null
                  }
                  onReject={
                    !eval_.hr_decision && eval_.recommendation
                      ? () => handleReject(candidateDetail.candidate.id)
                      : null
                  }
                  onOverride={
                    !eval_.hr_decision && eval_.recommendation
                      ? (reason) => handleOverride(candidateDetail.candidate.id, reason)
                      : null
                  }
                />
              ))}
            </div>
          ) : (
            <Card>
              <p className="text-sm text-navy-400 text-center py-8">
                {t("pipeline.selectCandidate")}
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
