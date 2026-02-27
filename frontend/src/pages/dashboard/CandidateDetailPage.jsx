import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { candidatesApi } from "../../api/candidates";
import { commentsApi } from "../../api/comments";
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
        className="text-sm text-navy-500 hover:text-navy-700 mb-4 flex items-center gap-1"
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
            <h1 className="text-2xl font-bold text-navy-900">{candidate.full_name}</h1>
            <p className="text-navy-500">{candidate.email}</p>
            {candidate.reference_id && (
              <p className="text-sm text-navy-400 force-ltr mt-1">
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
          className="block w-full rounded-lg border border-navy-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
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
          <p className="text-sm text-navy-500 mb-4">{answer.question_text}</p>

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
                  <p className="text-sm font-medium text-navy-700 mb-1">
                    {t("candidate.strengths")}
                  </p>
                  <ul className="list-disc list-inside text-sm text-navy-500 space-y-0.5">
                    {answer.scores.strengths.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {answer.scores.improvements?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-navy-700 mb-1">
                    {t("candidate.improvements")}
                  </p>
                  <ul className="list-disc list-inside text-sm text-navy-500 space-y-0.5">
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
              <p className="mt-2 text-navy-500 whitespace-pre-wrap bg-navy-50 p-3 rounded-lg">
                {answer.transcript}
              </p>
            </details>
          )}

          {answer.processing_status === "processing" && (
            <p className="text-sm text-amber-600">{t("candidate.processing")}</p>
          )}
        </Card>
      ))}

      {/* Discussion / Comments */}
      <DiscussionSection candidateId={id} t={t} />

      {/* PDPL Erasure */}
      <Card className="border-red-200 mt-8">
        <h3 className="text-sm font-semibold text-red-700 mb-2">{t("candidate.eraseData")}</h3>
        <p className="text-sm text-navy-500 mb-4">{t("candidate.eraseConfirm")}</p>
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
        <p className="text-sm text-navy-500 mb-6">{t("candidate.eraseConfirm")}</p>
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

function DiscussionSection({ candidateId, t }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [replyTo, setReplyTo] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    loadComments();
  }, [candidateId]);

  const loadComments = async () => {
    try {
      const res = await commentsApi.list(candidateId);
      setComments(res.data.comments || []);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  };

  const handlePost = async () => {
    if (!newComment.trim()) return;
    setPosting(true);
    try {
      await commentsApi.create(candidateId, { content: newComment.trim() });
      setNewComment("");
      loadComments();
    } catch {
      // Handle silently
    } finally {
      setPosting(false);
    }
  };

  const handleReply = async (parentId) => {
    if (!replyText.trim()) return;
    setPosting(true);
    try {
      await commentsApi.create(candidateId, {
        content: replyText.trim(),
        parent_id: parentId,
      });
      setReplyTo(null);
      setReplyText("");
      loadComments();
    } catch {
      // Handle silently
    } finally {
      setPosting(false);
    }
  };

  const topLevel = comments.filter((c) => !c.parent_id);
  const replies = comments.filter((c) => c.parent_id);

  const getReplies = (parentId) =>
    replies.filter((r) => r.parent_id === parentId);

  const formatTime = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return t("discussion.justNow");
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <Card className="mb-6">
      <h2 className="text-lg font-semibold text-navy-900 mb-4">
        {t("discussion.title")}
      </h2>

      {/* New comment input */}
      <div className="flex gap-3 mb-6">
        <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-sm font-bold shrink-0">
          U
        </div>
        <div className="flex-1">
          <textarea
            rows={2}
            className="block w-full rounded-lg border border-navy-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder={t("discussion.placeholder")}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handlePost();
            }}
          />
          <div className="flex justify-end mt-2">
            <Button size="sm" onClick={handlePost} loading={posting} disabled={!newComment.trim()}>
              {t("discussion.post")}
            </Button>
          </div>
        </div>
      </div>

      {/* Comments list */}
      {loading ? (
        <div className="flex justify-center py-4">
          <Spinner />
        </div>
      ) : topLevel.length === 0 ? (
        <p className="text-sm text-navy-400 text-center py-4">
          {t("discussion.noComments")}
        </p>
      ) : (
        <div className="space-y-4">
          {topLevel.map((comment) => (
            <div key={comment.id}>
              {/* Top-level comment */}
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-navy-100 text-navy-600 flex items-center justify-center text-sm font-bold shrink-0">
                  {(comment.author_name || "U").charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold text-navy-900">
                      {comment.author_name || "User"}
                    </span>
                    <span className="text-xs text-navy-400">
                      {formatTime(comment.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-navy-700 whitespace-pre-wrap">
                    {comment.content}
                  </p>
                  <button
                    onClick={() =>
                      setReplyTo(replyTo === comment.id ? null : comment.id)
                    }
                    className="text-xs text-primary-600 hover:text-primary-700 mt-1 font-medium"
                  >
                    {t("discussion.reply")}
                  </button>
                </div>
              </div>

              {/* Replies */}
              {getReplies(comment.id).map((reply) => (
                <div key={reply.id} className="flex gap-3 ms-11 mt-3">
                  <div className="w-6 h-6 rounded-full bg-navy-100 text-navy-500 flex items-center justify-center text-xs font-bold shrink-0">
                    {(reply.author_name || "U").charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-semibold text-navy-800">
                        {reply.author_name || "User"}
                      </span>
                      <span className="text-xs text-navy-400">
                        {formatTime(reply.created_at)}
                      </span>
                    </div>
                    <p className="text-sm text-navy-600 whitespace-pre-wrap">
                      {reply.content}
                    </p>
                  </div>
                </div>
              ))}

              {/* Reply input */}
              {replyTo === comment.id && (
                <div className="flex gap-3 ms-11 mt-3">
                  <div className="flex-1">
                    <textarea
                      rows={1}
                      className="block w-full rounded-lg border border-navy-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder={t("discussion.replyPlaceholder")}
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && (e.metaKey || e.ctrlKey))
                          handleReply(comment.id);
                      }}
                      autoFocus
                    />
                    <div className="flex justify-end gap-2 mt-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setReplyTo(null);
                          setReplyText("");
                        }}
                      >
                        {t("common.cancel")}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleReply(comment.id)}
                        loading={posting}
                        disabled={!replyText.trim()}
                      >
                        {t("discussion.reply")}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ScoreBar({ label, score }) {
  if (score == null) return null;
  const rounded = Math.round(score);
  const color =
    rounded >= 70 ? "bg-primary-500" : rounded >= 50 ? "bg-accent-500" : "bg-red-500";

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-navy-500">{label}</span>
        <span className="font-medium">{rounded}/100</span>
      </div>
      <div className="w-full bg-navy-200 rounded-full h-2">
        <div
          className={clsx("h-2 rounded-full transition-all", color)}
          style={{ width: `${rounded}%` }}
        />
      </div>
    </div>
  );
}
