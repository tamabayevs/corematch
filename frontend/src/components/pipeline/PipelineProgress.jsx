import { useI18n } from "../../lib/i18n";
import clsx from "clsx";

const STAGES = [
  { stage: 1, key: "cv_screening", icon: DocIcon },
  { stage: 2, key: "video_scoring", icon: VideoIcon },
  { stage: 3, key: "deep_evaluation", icon: BrainIcon },
  { stage: 4, key: "shortlist_ranking", icon: StarIcon },
];

export default function PipelineProgress({ currentStage = 0, evaluations = [] }) {
  const { t } = useI18n();

  const getStageStatus = (stage) => {
    const eval_ = evaluations.find((e) => e.stage === stage);
    if (!eval_) return currentStage >= stage ? "active" : "upcoming";
    if (eval_.hr_decision === "approved") return "approved";
    if (eval_.hr_decision === "rejected") return "rejected";
    if (eval_.recommendation) return "complete";
    return "active";
  };

  return (
    <div className="flex items-center gap-1">
      {STAGES.map((s, i) => {
        const status = getStageStatus(s.stage);
        return (
          <div key={s.stage} className="flex items-center">
            <div
              className={clsx(
                "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors",
                status === "approved" && "bg-green-100 text-green-800",
                status === "rejected" && "bg-red-100 text-red-800",
                status === "complete" && "bg-amber-100 text-amber-800",
                status === "active" && "bg-primary-100 text-primary-800 ring-2 ring-primary-300",
                status === "upcoming" && "bg-navy-100 text-navy-400"
              )}
            >
              <s.icon className="w-4 h-4" />
              <span className="hidden sm:inline">
                {t(`pipeline.stage.${s.key}`)}
              </span>
              <span className="sm:hidden">{s.stage}</span>
            </div>
            {i < STAGES.length - 1 && (
              <svg className="w-4 h-4 text-navy-300 mx-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}
          </div>
        );
      })}
    </div>
  );
}

function DocIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function VideoIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  );
}

function BrainIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  );
}

function StarIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
    </svg>
  );
}
