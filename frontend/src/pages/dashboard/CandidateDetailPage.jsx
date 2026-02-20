import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { candidatesApi } from "../../api/candidates";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import Spinner from "../../components/ui/Spinner";
import ScoreBadge from "../../components/ui/ScoreBadge";
import clsx from "clsx";

export default function CandidateDetailPage() {
  const { id } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [decisionNote, setDecisionNote] = useState("");
  const [showEraseModal, setShowEraseModal] = useState(false);
  const [eraseLoading, setEraseLoading] = useState(false);

  useEffect(() => {
    loadCandidate();
  }, [id]);

  const loadCandidate = async () => {
    try {
      const res = await candidatesApi.get(id);
      setCandidate(res.data.candidate);
      setDecisionNote(res.data.candidate.hr_decision_note || "");
    } catch {
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (decision) => {
    try {
      await candidatesApi.updateDecision(id, decision, decisionNote);
      loadCandidate();
    } catch {
      // Handle error
    }
  };

  const handleErase = async () => {
    setEraseLoading(true);
    try {
      await candidatesApi.erase(id);
      navigate("/dashboard");
    } catch {
      // Handle error
    } finally {
      setEraseLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (!candidate) return null;

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => navigate(`/dashboard/campaigns/${candidate.campaign_id}`)}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 flex items-center gap-1"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        {t("common.back")}
      </button>

      {/* Header */}
      <Card className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{candidate.full_name}</h1>
            <p className="text-gray-500">{candidate.email}</p>
            {candidate.reference_id && (
              <p className="text-sm text-gray-400 force-ltr mt-1">
                {t("candidate.referenceId")}: {candidate.reference_id}
              </p>
            )}
          </div>
          {candidate.overall_score != null && (
            <ScoreBadge score={candidate.overall_score} tier={candidate.tier} size="lg" />
          )}
        </div>
      </Card>

      {/* Decision controls */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold mb-4">{t("candidate.setDecision")}</h2>
        <div className="flex gap-3 mb-4">
          <Button
            variant={candidate.hr_decision === "shortlisted" ? "success" : "secondary"}
            onClick={() => handleDecision("shortlisted")}
            size="sm"
          >
            {t("candidate.shortlist")}
          </Button>
          <Button
            variant={candidate.hr_decision === "hold" ? "warning" : "secondary"}
            onClick={() => handleDecision("hold")}
            size="sm"
          >
            {t("candidate.hold")}
          </Button>
          <Button
            variant={candidate.hr_decision === "rejected" ? "danger" : "secondary"}
            onClick={() => handleDecision("rejected")}
            size="sm"
          >
            {t("candidate.reject")}
          </Button>
          {candidate.hr_decision && (
            <Button variant="ghost" onClick={() => handleDecision(null)} size="sm">
              {t("candidate.clearDecision")}
            </Button>
          )}
        </div>
        <textarea
          rows={2}
          className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder={t("candidate.decisionNote")}
          value={decisionNote}
          onChange={(e) => setDecisionNote(e.target.value)}
        />
      </Card>

      {/* Video answers */}
      {candidate.video_answers?.map((answer) => (
        <Card key={answer.id} className="mb-4">
          <h3 className="font-semibold mb-3">
            {t("candidate.videoAnswer", { index: answer.question_index + 1 })}
          </h3>
          <p className="text-sm text-gray-600 mb-4">{answer.question_text}</p>

          {answer.signed_url && (
            <video
              controls
              className="w-full rounded-lg bg-black mb-4"
              style={{ maxHeight: 400 }}
            >
              <source src={answer.signed_url} type={`video/${answer.file_format || "webm"}`} />
            </video>
          )}

          {answer.scores && (
            <div className="space-y-3 mb-4">
              <ScoreBar label={t("candidate.content")} score={answer.scores.content} />
              <ScoreBar label={t("candidate.communication")} score={answer.scores.communication} />
              <ScoreBar label={t("candidate.behavioral")} score={answer.scores.behavioral} />

              {answer.scores.strengths?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">
                    {t("candidate.strengths")}
                  </p>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
                    {answer.scores.strengths.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {answer.scores.improvements?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">
                    {t("candidate.improvements")}
                  </p>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
                    {answer.scores.improvements.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {answer.transcript && (
            <details className="text-sm">
              <summary className="cursor-pointer text-primary-600 hover:text-primary-700 font-medium">
                {t("candidate.transcript")}
              </summary>
              <p className="mt-2 text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded-lg">
                {answer.transcript}
              </p>
            </details>
          )}

          {answer.processing_status === "processing" && (
            <p className="text-sm text-amber-600">{t("candidate.processing")}</p>
          )}
        </Card>
      ))}

      {/* PDPL Erasure */}
      <Card className="border-red-200 mt-8">
        <h3 className="text-sm font-semibold text-red-700 mb-2">{t("candidate.eraseData")}</h3>
        <p className="text-sm text-gray-500 mb-4">{t("candidate.eraseConfirm")}</p>
        <Button variant="danger" size="sm" onClick={() => setShowEraseModal(true)}>
          {t("candidate.eraseData")}
        </Button>
      </Card>

      {/* Erase confirmation modal */}
      <Modal
        open={showEraseModal}
        onClose={() => setShowEraseModal(false)}
        title={t("candidate.eraseData")}
      >
        <p className="text-sm text-gray-600 mb-6">{t("candidate.eraseConfirm")}</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setShowEraseModal(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant="danger" onClick={handleErase} loading={eraseLoading}>
            {t("common.confirm")}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function ScoreBar({ label, score }) {
  if (score == null) return null;
  const rounded = Math.round(score);
  const color =
    rounded >= 70 ? "bg-green-500" : rounded >= 50 ? "bg-amber-500" : "bg-red-500";

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{rounded}/100</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={clsx("h-2 rounded-full transition-all", color)}
          style={{ width: `${rounded}%` }}
        />
      </div>
    </div>
  );
}
