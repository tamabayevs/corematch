import clsx from "clsx";
import { useI18n } from "../../lib/i18n";

function getTierInfo(score, tier) {
  if (tier === "strong_proceed" || score >= 70) {
    return { color: "text-green-600", bg: "bg-green-50 border-green-200", label: "candidate.strongProceed" };
  }
  if (tier === "consider" || score >= 50) {
    return { color: "text-amber-600", bg: "bg-amber-50 border-amber-200", label: "candidate.consider" };
  }
  return { color: "text-red-600", bg: "bg-red-50 border-red-200", label: "candidate.likelyPass" };
}

export default function ScoreBadge({ score, tier, size = "md" }) {
  const { t } = useI18n();

  if (score == null) return null;

  const info = getTierInfo(score, tier);
  const roundedScore = Math.round(score);

  if (size === "lg") {
    return (
      <div className={clsx("flex flex-col items-center p-4 rounded-xl border", info.bg)}>
        <span className={clsx("text-3xl font-bold", info.color)}>{roundedScore}</span>
        <span className={clsx("text-sm font-medium mt-1", info.color)}>
          {t(info.label)}
        </span>
      </div>
    );
  }

  return (
    <div className={clsx("inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border", info.bg)}>
      <span className={clsx("text-sm font-semibold", info.color)}>{roundedScore}</span>
      <span className={clsx("text-xs", info.color)}>{t(info.label)}</span>
    </div>
  );
}
