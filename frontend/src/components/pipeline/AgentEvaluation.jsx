import { useState } from "react";
import { useI18n } from "../../lib/i18n";
import clsx from "clsx";

const RECOMMENDATION_COLORS = {
  advance: { bg: "bg-green-100", text: "text-green-800", ring: "ring-green-300" },
  reject: { bg: "bg-red-100", text: "text-red-800", ring: "ring-red-300" },
  needs_review: { bg: "bg-amber-100", text: "text-amber-800", ring: "ring-amber-300" },
};

export default function AgentEvaluation({ evaluation, onApprove, onReject, onOverride }) {
  const { t } = useI18n();
  const [showEvidence, setShowEvidence] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [showOverride, setShowOverride] = useState(false);

  if (!evaluation) return null;

  const {
    overall_score,
    scores_detail = {},
    recommendation,
    confidence,
    summary,
    strengths = [],
    concerns = [],
    evidence = [],
    hr_decision,
    hr_override_reason,
    provider,
    model_used,
    agent_type,
    stage,
  } = evaluation;

  const recColors = RECOMMENDATION_COLORS[recommendation] || RECOMMENDATION_COLORS.needs_review;
  const isAwaitingDecision = !hr_decision && recommendation;

  return (
    <div className="border border-navy-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="bg-navy-50 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-navy-800">
            {t(`pipeline.agent.${agent_type}`)}
          </span>
          <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full", recColors.bg, recColors.text)}>
            {t(`pipeline.recommendation.${recommendation}`)}
          </span>
        </div>
        {hr_decision && (
          <span className={clsx(
            "text-xs font-medium px-2 py-0.5 rounded-full",
            hr_decision === "approved" && "bg-green-100 text-green-800",
            hr_decision === "rejected" && "bg-red-100 text-red-800",
            hr_decision === "overridden" && "bg-purple-100 text-purple-800"
          )}>
            {t(`pipeline.hr_decision.${hr_decision}`)}
          </span>
        )}
      </div>

      {/* Score ring + details */}
      <div className="p-4 space-y-4">
        <div className="flex items-start gap-6">
          {/* Score gauge */}
          <div className="flex-shrink-0 text-center">
            <div className="relative w-20 h-20">
              <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="3"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke={overall_score >= 70 ? "#10b981" : overall_score >= 40 ? "#f59e0b" : "#ef4444"}
                  strokeWidth="3"
                  strokeDasharray={`${overall_score}, 100`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-navy-900">{Math.round(overall_score || 0)}</span>
              </div>
            </div>
            {confidence != null && (
              <p className="text-[10px] text-navy-400 mt-1">
                {t("pipeline.confidence")}: {Math.round(confidence * 100)}%
              </p>
            )}
          </div>

          {/* Sub-scores */}
          <div className="flex-1 space-y-2">
            {Object.entries(scores_detail).map(([key, value]) => (
              <div key={key}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span className="text-navy-600">{t(`pipeline.score.${key}`) || key}</span>
                  <span className="font-medium text-navy-800">{Math.round(value)}</span>
                </div>
                <div className="w-full bg-navy-100 rounded-full h-1.5">
                  <div
                    className={clsx(
                      "h-1.5 rounded-full",
                      value >= 70 ? "bg-green-500" : value >= 40 ? "bg-amber-500" : "bg-red-500"
                    )}
                    style={{ width: `${Math.min(value, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Summary */}
        {summary && (
          <p className="text-sm text-navy-700 bg-navy-50 rounded-lg p-3">{summary}</p>
        )}

        {/* Strengths / Concerns */}
        <div className="grid grid-cols-2 gap-4">
          {strengths.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-green-700 mb-1">{t("pipeline.strengths")}</h4>
              <ul className="space-y-1">
                {strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-navy-600">
                    <svg className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {concerns.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-amber-700 mb-1">{t("pipeline.concerns")}</h4>
              <ul className="space-y-1">
                {concerns.map((c, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-navy-600">
                    <svg className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
                    </svg>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Evidence (collapsible) */}
        {evidence.length > 0 && (
          <div>
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
            >
              {showEvidence ? t("pipeline.hideEvidence") : t("pipeline.showEvidence")}
              ({evidence.length})
              <svg className={clsx("w-3 h-3 transition-transform", showEvidence && "rotate-180")} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showEvidence && (
              <div className="mt-2 space-y-1.5">
                {evidence.map((e, i) => (
                  <div key={i} className="bg-navy-50 rounded-lg p-2.5 text-xs">
                    <span className="font-medium text-navy-700">{e.claim}</span>
                    {e.source && (
                      <span className="text-navy-400 ms-2">({e.source})</span>
                    )}
                    {e.detail && (
                      <p className="text-navy-500 mt-0.5 italic">"{e.detail}"</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* HR Override reason display */}
        {hr_override_reason && (
          <div className="bg-purple-50 rounded-lg p-3 text-xs">
            <span className="font-medium text-purple-800">{t("pipeline.overrideReason")}:</span>
            <span className="text-purple-700 ms-1">{hr_override_reason}</span>
          </div>
        )}

        {/* Action buttons (only when awaiting HR decision) */}
        {isAwaitingDecision && (
          <div className="flex items-center gap-2 pt-2 border-t border-navy-100">
            {onApprove && (
              <button
                onClick={onApprove}
                className="flex-1 py-2 px-3 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
              >
                {t("pipeline.approve")}
              </button>
            )}
            {onReject && (
              <button
                onClick={onReject}
                className="flex-1 py-2 px-3 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
              >
                {t("pipeline.reject")}
              </button>
            )}
            {onOverride && !showOverride && (
              <button
                onClick={() => setShowOverride(true)}
                className="py-2 px-3 bg-navy-100 text-navy-700 text-sm font-medium rounded-lg hover:bg-navy-200 transition-colors"
              >
                {t("pipeline.override")}
              </button>
            )}
          </div>
        )}

        {/* Override form */}
        {showOverride && (
          <div className="pt-2 space-y-2 border-t border-navy-100">
            <textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder={t("pipeline.overridePlaceholder")}
              className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              rows={2}
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  if (overrideReason.trim() && onOverride) {
                    onOverride(overrideReason.trim());
                    setShowOverride(false);
                    setOverrideReason("");
                  }
                }}
                disabled={!overrideReason.trim()}
                className="py-1.5 px-3 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {t("pipeline.submitOverride")}
              </button>
              <button
                onClick={() => {
                  setShowOverride(false);
                  setOverrideReason("");
                }}
                className="py-1.5 px-3 bg-navy-100 text-navy-700 text-sm rounded-lg hover:bg-navy-200"
              >
                {t("common.cancel")}
              </button>
            </div>
          </div>
        )}

        {/* Provider info */}
        {provider && (
          <p className="text-[10px] text-navy-400 pt-1">
            {provider} / {model_used}
          </p>
        )}
      </div>
    </div>
  );
}
