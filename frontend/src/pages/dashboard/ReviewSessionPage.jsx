import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { candidatesApi } from "../../api/candidates";
import api from "../../api/client";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import ScoreBadge from "../../components/ui/ScoreBadge";
import Spinner from "../../components/ui/Spinner";
import clsx from "clsx";

const PLAYBACK_SPEEDS = [0.75, 1, 1.25, 1.5, 2];

const TIER_VARIANTS = {
  strong_proceed: "teal",
  consider: "amber",
  likely_pass: "red",
};

export default function ReviewSessionPage() {
  const { candidateId } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const videoRef = useRef(null);

  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeQuestion, setActiveQuestion] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [decision, setDecision] = useState(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Load candidate data
  useEffect(() => {
    const loadCandidate = async () => {
      setLoading(true);
      try {
        const res = await candidatesApi.get(candidateId);
        const c = res.data.candidate;
        setCandidate(c);
        setDecision(c.hr_decision || null);
        setNote(c.hr_decision_note || "");
      } catch {
        navigate("/dashboard/reviews");
      } finally {
        setLoading(false);
      }
    };
    loadCandidate();
  }, [candidateId, navigate]);

  // Update video playback speed when it changes
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackSpeed;
    }
  }, [playbackSpeed, activeQuestion]);

  // Ensure playback speed is applied when video loads
  const handleVideoLoaded = () => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackSpeed;
    }
  };

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e) => {
      // Don't capture keys when typing in textarea
      if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") {
        return;
      }

      switch (e.key) {
        case " ": {
          e.preventDefault();
          const video = videoRef.current;
          if (video) {
            if (video.paused) {
              video.play();
            } else {
              video.pause();
            }
          }
          break;
        }
        case "ArrowLeft": {
          e.preventDefault();
          const video = videoRef.current;
          if (video) {
            video.currentTime = Math.max(0, video.currentTime - 10);
          }
          break;
        }
        case "ArrowRight": {
          e.preventDefault();
          const video = videoRef.current;
          if (video) {
            video.currentTime = Math.min(
              video.duration || 0,
              video.currentTime + 10
            );
          }
          break;
        }
        case "1":
          setPlaybackSpeed(0.75);
          break;
        case "2":
          setPlaybackSpeed(1);
          break;
        case "3":
          setPlaybackSpeed(1.25);
          break;
        case "4":
          setPlaybackSpeed(1.5);
          break;
        case "5":
          setPlaybackSpeed(2);
          break;
        case "s":
        case "S":
          setDecision("shortlisted");
          break;
        case "h":
        case "H":
          setDecision("hold");
          break;
        case "r":
        case "R":
          setDecision("rejected");
          break;
        case "n":
        case "N":
          handleSaveAndNext();
          break;
        case "?":
          setShowHelp((prev) => !prev);
          break;
        default:
          break;
      }
    },
    [playbackSpeed]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Save decision and mark as reviewed
  const handleSaveDecision = async () => {
    if (!decision) return;
    setSaving(true);
    try {
      await candidatesApi.updateDecision(candidateId, decision, note);
      await api.put(`/candidates/${candidateId}/reviewed`);
      // Reload to reflect changes
      const res = await candidatesApi.get(candidateId);
      setCandidate(res.data.candidate);
    } catch {
      // Handle silently
    } finally {
      setSaving(false);
    }
  };

  // Save and navigate to next
  const handleSaveAndNext = async () => {
    if (decision) {
      setSaving(true);
      try {
        await candidatesApi.updateDecision(candidateId, decision, note);
        await api.put(`/candidates/${candidateId}/reviewed`);
      } catch {
        // Handle silently
      } finally {
        setSaving(false);
      }
    }
    // Navigate back to queue to pick next candidate
    navigate("/dashboard/reviews");
  };

  const tierLabel = (tier) => {
    if (!tier) return null;
    const keyMap = {
      strong_proceed: "strongProceed",
      consider: "consider",
      likely_pass: "likelyPass",
    };
    return t(`candidate.${keyMap[tier] || tier}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (!candidate) return null;

  const videoAnswers = candidate.video_answers || [];
  const currentAnswer = videoAnswers[activeQuestion] || null;

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard/reviews")}
            className="text-sm text-navy-500 hover:text-navy-700 flex items-center gap-1"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            {t("common.back")}
          </button>
          <div className="h-5 w-px bg-navy-200" />
          <h1 className="text-lg font-bold text-navy-900">
            {candidate.full_name}
          </h1>
          {candidate.campaign_name && (
            <span className="text-sm text-navy-400">
              {candidate.campaign_name}
            </span>
          )}
        </div>
        <button
          onClick={() => setShowHelp(true)}
          className="text-sm text-navy-400 hover:text-navy-600 flex items-center gap-1"
          title={t("review.keyboardShortcuts")}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {t("review.shortcuts")}
        </button>
      </div>

      {/* Main content: Video + AI panel */}
      <div className="flex gap-4 flex-1 min-h-0 mb-4">
        {/* Left: Video player (60%) */}
        <div className="w-3/5 flex flex-col min-h-0">
          {/* Question tabs */}
          {videoAnswers.length > 1 && (
            <div className="flex gap-1 mb-3 bg-navy-100 rounded-lg p-1 overflow-x-auto">
              {videoAnswers.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveQuestion(idx)}
                  className={clsx(
                    "px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap",
                    activeQuestion === idx
                      ? "bg-white text-navy-900 shadow-sm"
                      : "text-navy-500 hover:text-navy-700"
                  )}
                >
                  {t("review.question", { number: idx + 1 })}
                </button>
              ))}
            </div>
          )}

          {/* Question text */}
          {currentAnswer && (
            <Card className="!p-3 mb-3">
              <p className="text-sm text-navy-700 font-medium">
                {t("review.questionLabel", {
                  number: activeQuestion + 1,
                })}
              </p>
              <p className="text-sm text-navy-500 mt-1">
                {currentAnswer.question_text}
              </p>
            </Card>
          )}

          {/* Video */}
          {currentAnswer?.signed_url ? (
            <div className="flex-1 min-h-0 flex flex-col">
              <div className="relative bg-black rounded-xl overflow-hidden flex-1">
                <video
                  ref={videoRef}
                  key={currentAnswer.signed_url}
                  controls
                  className="w-full h-full object-contain"
                  onLoadedData={handleVideoLoaded}
                >
                  <source
                    src={currentAnswer.signed_url}
                    type={`video/${currentAnswer.file_format || "webm"}`}
                  />
                </video>
              </div>

              {/* Playback speed selector */}
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-navy-500 font-medium">
                  {t("review.speed")}:
                </span>
                <div className="flex gap-1">
                  {PLAYBACK_SPEEDS.map((speed) => (
                    <button
                      key={speed}
                      onClick={() => setPlaybackSpeed(speed)}
                      className={clsx(
                        "px-2 py-0.5 rounded text-xs font-medium transition-colors",
                        playbackSpeed === speed
                          ? "bg-primary-100 text-primary-700 border border-primary-200"
                          : "bg-navy-100 text-navy-500 hover:text-navy-700 border border-transparent"
                      )}
                    >
                      {speed}x
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center bg-navy-50 rounded-xl">
              <p className="text-sm text-navy-400">
                {t("review.noVideo")}
              </p>
            </div>
          )}
        </div>

        {/* Right: AI Summary + Transcript (40%) */}
        <div className="w-2/5 flex flex-col gap-4 min-h-0 overflow-y-auto">
          {/* AI Summary card */}
          <Card>
            <div className="flex items-start justify-between mb-4">
              <h3 className="font-semibold text-navy-900">
                {t("review.aiSummary")}
              </h3>
              {candidate.overall_score != null && (
                <ScoreBadge
                  score={candidate.overall_score}
                  tier={candidate.tier}
                />
              )}
            </div>

            {/* Tier */}
            {candidate.tier && (
              <div className="mb-4">
                <Badge variant={TIER_VARIANTS[candidate.tier]}>
                  {tierLabel(candidate.tier)}
                </Badge>
              </div>
            )}

            {/* Per-question scores for current answer */}
            {currentAnswer?.scores && (
              <div className="space-y-3 mb-4">
                <ScoreRow
                  label={t("candidate.content")}
                  score={currentAnswer.scores.content}
                />
                <ScoreRow
                  label={t("candidate.communication")}
                  score={currentAnswer.scores.communication}
                />
                <ScoreRow
                  label={t("candidate.behavioral")}
                  score={currentAnswer.scores.behavioral}
                />
              </div>
            )}

            {/* Strengths */}
            {currentAnswer?.scores?.strengths?.length > 0 && (
              <div className="mb-3">
                <p className="text-sm font-medium text-navy-700 mb-1.5">
                  {t("candidate.strengths")}
                </p>
                <ul className="space-y-1">
                  {currentAnswer.scores.strengths.map((s, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-navy-600"
                    >
                      <svg
                        className="w-4 h-4 text-primary-500 shrink-0 mt-0.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Improvements */}
            {currentAnswer?.scores?.improvements?.length > 0 && (
              <div>
                <p className="text-sm font-medium text-navy-700 mb-1.5">
                  {t("candidate.improvements")}
                </p>
                <ul className="space-y-1">
                  {currentAnswer.scores.improvements.map((s, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-navy-600"
                    >
                      <svg
                        className="w-4 h-4 text-accent-500 shrink-0 mt-0.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                      </svg>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* Transcript card */}
          {currentAnswer?.transcript && (
            <Card>
              <h3 className="font-semibold text-navy-900 mb-3">
                {t("candidate.transcript")}
              </h3>
              <p className="text-sm text-navy-600 whitespace-pre-wrap bg-navy-50 p-3 rounded-lg leading-relaxed max-h-64 overflow-y-auto">
                {currentAnswer.transcript}
              </p>
            </Card>
          )}
        </div>
      </div>

      {/* Bottom bar (sticky) */}
      <div className="sticky bottom-0 bg-white border-t border-navy-200 -mx-6 px-6 py-4 mt-auto">
        <div className="flex items-center gap-4">
          {/* Decision buttons */}
          <div className="flex gap-2">
            <Button
              variant={decision === "shortlisted" ? "success" : "secondary"}
              size="sm"
              onClick={() =>
                setDecision(
                  decision === "shortlisted" ? null : "shortlisted"
                )
              }
            >
              <svg
                className="w-4 h-4 me-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              {t("candidate.shortlist")}
              <kbd className="ms-1.5 text-[10px] opacity-60 font-mono">S</kbd>
            </Button>
            <Button
              variant={decision === "hold" ? "warning" : "secondary"}
              size="sm"
              onClick={() =>
                setDecision(decision === "hold" ? null : "hold")
              }
            >
              <svg
                className="w-4 h-4 me-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {t("candidate.hold")}
              <kbd className="ms-1.5 text-[10px] opacity-60 font-mono">H</kbd>
            </Button>
            <Button
              variant={decision === "rejected" ? "danger" : "secondary"}
              size="sm"
              onClick={() =>
                setDecision(decision === "rejected" ? null : "rejected")
              }
            >
              <svg
                className="w-4 h-4 me-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              {t("candidate.reject")}
              <kbd className="ms-1.5 text-[10px] opacity-60 font-mono">R</kbd>
            </Button>
          </div>

          {/* Note */}
          <textarea
            rows={1}
            className="flex-1 rounded-lg border border-navy-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            placeholder={t("candidate.decisionNote")}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />

          {/* Save + Next */}
          <div className="flex gap-2">
            {decision && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSaveDecision}
                loading={saving}
              >
                {t("review.saveDecision")}
              </Button>
            )}
            <Button size="sm" onClick={handleSaveAndNext} loading={saving}>
              {t("review.nextCandidate")}
              <kbd className="ms-1.5 text-[10px] opacity-60 font-mono">N</kbd>
            </Button>
          </div>
        </div>
      </div>

      {/* Keyboard shortcuts help overlay */}
      {showHelp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowHelp(false)}
        >
          <Card
            className="w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-navy-900">
                {t("review.keyboardShortcuts")}
              </h3>
              <button
                onClick={() => setShowHelp(false)}
                className="text-navy-400 hover:text-navy-600"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="space-y-2">
              <ShortcutRow
                keys={t("review.shortcutSpace")}
                action={t("review.shortcutPlayPause")}
              />
              <ShortcutRow
                keys={t("review.shortcutArrows")}
                action={t("review.shortcutSeek")}
              />
              <ShortcutRow
                keys="1-5"
                action={t("review.shortcutSpeed")}
              />
              <div className="border-t border-navy-100 my-2" />
              <ShortcutRow
                keys="S"
                action={t("candidate.shortlist")}
              />
              <ShortcutRow keys="H" action={t("candidate.hold")} />
              <ShortcutRow keys="R" action={t("candidate.reject")} />
              <ShortcutRow
                keys="N"
                action={t("review.nextCandidate")}
              />
              <div className="border-t border-navy-100 my-2" />
              <ShortcutRow
                keys="?"
                action={t("review.shortcutToggleHelp")}
              />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────

function ScoreRow({ label, score }) {
  if (score == null) return null;
  const rounded = Math.round(score);
  const color =
    rounded >= 70
      ? "bg-primary-500"
      : rounded >= 50
        ? "bg-accent-500"
        : "bg-red-500";

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-navy-500">{label}</span>
        <span className="font-medium text-navy-700">{rounded}/100</span>
      </div>
      <div className="w-full bg-navy-200 rounded-full h-1.5">
        <div
          className={clsx("h-1.5 rounded-full transition-all", color)}
          style={{ width: `${rounded}%` }}
        />
      </div>
    </div>
  );
}

function ShortcutRow({ keys, action }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-navy-600">{action}</span>
      <kbd className="px-2 py-0.5 bg-navy-100 border border-navy-200 rounded text-xs font-mono text-navy-700">
        {keys}
      </kbd>
    </div>
  );
}
