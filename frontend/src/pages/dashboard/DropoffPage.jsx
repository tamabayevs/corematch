import { useEffect, useState } from "react";
import { useI18n } from "../../lib/i18n";
import { campaignsApi } from "../../api/campaigns";
import api from "../../api/client";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import clsx from "clsx";

export default function DropoffPage() {
  const { t } = useI18n();

  // Filters
  const [campaignId, setCampaignId] = useState("");
  const [campaignsList, setCampaignsList] = useState([]);

  // Data
  const [questionPerformance, setQuestionPerformance] = useState(null);
  const [abandonmentData, setAbandonmentData] = useState(null);
  const [campaignCompletion, setCampaignCompletion] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load campaigns for dropdown
  useEffect(() => {
    campaignsApi.list().then((res) => {
      setCampaignsList(res.data.campaigns || []);
    }).catch(() => {});
  }, []);

  // Load drop-off data whenever filter changes
  useEffect(() => {
    loadData();
  }, [campaignId]);

  const buildParams = () => {
    const params = {};
    if (campaignId) params.campaign_id = campaignId;
    return { params };
  };

  const loadData = async () => {
    setLoading(true);
    const config = buildParams();
    try {
      const [questionRes, abandonRes, completionRes] = await Promise.all([
        api.get("/insights/question-performance", config),
        api.get("/insights/abandonment", config),
        api.get("/insights/campaign-completion", config),
      ]);
      setQuestionPerformance(questionRes.data);
      setAbandonmentData(abandonRes.data);
      setCampaignCompletion(completionRes.data);
    } catch {
      // Handle silently — empty states will render
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header + Filters */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("dropoff.title")}</h1>
          <p className="text-sm text-navy-500 mt-0.5">{t("dropoff.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col">
            <label className="text-xs font-medium text-navy-500 mb-1">
              {t("insights.campaign")}
            </label>
            <select
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              className="h-9 rounded-lg border border-navy-200 bg-white px-3 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">{t("insights.allCampaigns")}</option>
              {campaignsList.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : (
        <>
          {/* Per-Question Performance */}
          {questionPerformance && (
            <QuestionPerformanceChart data={questionPerformance} t={t} />
          )}

          {/* Abandonment Funnel */}
          {abandonmentData && (
            <AbandonmentChart data={abandonmentData} t={t} />
          )}

          {/* Campaign Completion Comparison */}
          {campaignCompletion && (
            <CampaignCompletionTable data={campaignCompletion} t={t} />
          )}
        </>
      )}
    </div>
  );
}

// ─── Per-Question Performance ─────────────────────────────────

function QuestionPerformanceChart({ data, t }) {
  const questions = data.questions || [];

  if (questions.length === 0) {
    return (
      <Card>
        <h3 className="font-semibold text-navy-900 mb-4">{t("dropoff.questionPerformance")}</h3>
        <p className="text-sm text-navy-400 text-center py-8">{t("insights.noData")}</p>
      </Card>
    );
  }

  const maxScore = 100;

  return (
    <Card>
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-semibold text-navy-900">{t("dropoff.questionPerformance")}</h3>
        <div className="flex items-center gap-4 text-[10px] text-navy-400">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm bg-primary-500" />
            {t("dropoff.avgScore")}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm bg-accent-400" />
            {t("dropoff.variance")}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {questions.map((q, idx) => {
          const avgPct = Math.max((q.avg_score / maxScore) * 100, 2);
          const variancePct = Math.max((q.score_variance / maxScore) * 100, 2);

          return (
            <div key={idx}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-medium text-navy-700 truncate max-w-[60%]">
                  {t("dropoff.questionLabel", { num: idx + 1 })}
                  {q.question_text && (
                    <span className="text-navy-400 font-normal ml-1.5 text-xs">
                      {q.question_text.length > 50
                        ? q.question_text.substring(0, 50) + "..."
                        : q.question_text}
                    </span>
                  )}
                </span>
                <span className="text-xs text-navy-500 shrink-0 ml-2">
                  {q.answer_count} {t("dropoff.answers")}
                </span>
              </div>

              {/* Avg Score Bar */}
              <div className="flex items-center gap-2 mb-1">
                <div className="flex-1 bg-navy-100 rounded-full h-5 overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full flex items-center justify-end px-2 transition-all"
                    style={{ width: `${avgPct}%`, minWidth: "2rem" }}
                  >
                    <span className="text-[10px] font-bold text-white">
                      {q.avg_score}
                    </span>
                  </div>
                </div>
              </div>

              {/* Variance Bar */}
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-navy-100 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full bg-accent-400 rounded-full transition-all"
                    style={{ width: `${variancePct}%`, minWidth: "1rem" }}
                  />
                </div>
                <span className="text-[10px] text-navy-400 w-16 shrink-0 text-end">
                  {t("dropoff.varianceLabel")}: {q.score_variance}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ─── Abandonment Chart ────────────────────────────────────────

function AbandonmentChart({ data, t }) {
  const stages = data.stages || [];

  if (stages.length === 0) {
    return (
      <Card>
        <h3 className="font-semibold text-navy-900 mb-4">{t("dropoff.abandonmentTitle")}</h3>
        <p className="text-sm text-navy-400 text-center py-8">{t("insights.noData")}</p>
      </Card>
    );
  }

  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  const stageColors = [
    "bg-primary-500",
    "bg-primary-400",
    "bg-accent-400",
    "bg-accent-300",
    "bg-red-400",
    "bg-red-300",
  ];

  return (
    <Card>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-semibold text-navy-900">{t("dropoff.abandonmentTitle")}</h3>
          <p className="text-xs text-navy-400 mt-0.5">{t("dropoff.abandonmentDesc")}</p>
        </div>
      </div>

      {/* Vertical bar chart */}
      <div className="flex items-end justify-around gap-3" style={{ height: "220px" }}>
        {stages.map((stage, idx) => {
          const heightPct = maxCount > 0 ? (stage.count / maxCount) * 100 : 0;
          const prev = idx > 0 ? stages[idx - 1] : null;
          const dropRate =
            prev && prev.count > 0
              ? Math.round(((prev.count - stage.count) / prev.count) * 100)
              : null;

          return (
            <div key={stage.name} className="flex flex-col items-center flex-1 h-full justify-end">
              {/* Count label */}
              <span className="text-xs font-bold text-navy-700 mb-1">
                {stage.count}
              </span>

              {/* Drop-off badge */}
              {dropRate !== null && dropRate > 0 && (
                <span className="text-[9px] font-medium text-red-500 mb-0.5">
                  -{dropRate}%
                </span>
              )}

              {/* Bar */}
              <div
                className={clsx(
                  "w-full max-w-[56px] rounded-t-md transition-all",
                  stageColors[idx % stageColors.length]
                )}
                style={{
                  height: `${Math.max(heightPct, 4)}%`,
                  minHeight: "6px",
                }}
              />

              {/* Label */}
              <span className="text-[10px] text-navy-500 mt-2 font-medium text-center leading-tight">
                {stage.label || stage.name}
              </span>
            </div>
          );
        })}
      </div>

      {/* Summary row */}
      {stages.length >= 2 && (
        <div className="mt-4 pt-4 border-t border-navy-100 flex items-center justify-between text-xs text-navy-500">
          <span>
            {t("dropoff.totalStarted")}: <strong className="text-navy-700">{stages[0].count}</strong>
          </span>
          <span>
            {t("dropoff.totalCompleted")}: <strong className="text-navy-700">{stages[stages.length - 1].count}</strong>
          </span>
          <span>
            {t("dropoff.overallDropoff")}:{" "}
            <strong className={clsx(
              "font-semibold",
              stages[0].count > 0 &&
                Math.round(((stages[0].count - stages[stages.length - 1].count) / stages[0].count) * 100) > 50
                ? "text-red-600"
                : "text-accent-600"
            )}>
              {stages[0].count > 0
                ? Math.round(((stages[0].count - stages[stages.length - 1].count) / stages[0].count) * 100)
                : 0}%
            </strong>
          </span>
        </div>
      )}
    </Card>
  );
}

// ─── Campaign Completion Comparison ───────────────────────────

function CampaignCompletionTable({ data, t }) {
  const campaigns = data.campaigns || [];

  if (campaigns.length === 0) {
    return (
      <Card>
        <h3 className="font-semibold text-navy-900 mb-4">{t("dropoff.completionComparison")}</h3>
        <p className="text-sm text-navy-400 text-center py-8">{t("insights.noData")}</p>
      </Card>
    );
  }

  // Sort by completion rate descending
  const sorted = [...campaigns].sort((a, b) => b.completion_rate - a.completion_rate);
  const maxInvited = Math.max(...sorted.map((c) => c.invited_count), 1);

  return (
    <Card className="overflow-hidden !p-0">
      <div className="p-6 pb-4">
        <h3 className="font-semibold text-navy-900">{t("dropoff.completionComparison")}</h3>
        <p className="text-xs text-navy-400 mt-0.5">{t("dropoff.completionDesc")}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-t border-b border-navy-200 bg-navy-50">
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("campaign.name")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("dropoff.invited")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("dropoff.started")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("dashboard.submitted")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider min-w-[200px]">
                {t("insights.completionRate")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("dropoff.dropoffRate")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-100">
            {sorted.map((c) => {
              const dropoff = c.invited_count > 0
                ? Math.round(((c.invited_count - c.submitted_count) / c.invited_count) * 100)
                : 0;

              return (
                <tr key={c.campaign_id} className="hover:bg-navy-50 transition-colors">
                  <td className="px-6 py-3 font-medium text-navy-800 truncate max-w-[200px]">
                    {c.name}
                  </td>
                  <td className="px-6 py-3 text-navy-600">{c.invited_count}</td>
                  <td className="px-6 py-3 text-navy-600">{c.started_count}</td>
                  <td className="px-6 py-3 text-navy-600">{c.submitted_count}</td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-navy-100 rounded-full h-2.5 max-w-[120px] overflow-hidden">
                        {/* Stacked bar: submitted (green) + started-but-not-submitted (amber) */}
                        <div className="h-full flex">
                          <div
                            className="h-full bg-primary-500 transition-all"
                            style={{
                              width: `${Math.min(c.completion_rate, 100)}%`,
                            }}
                          />
                          {c.started_count > c.submitted_count && c.invited_count > 0 && (
                            <div
                              className="h-full bg-accent-300 transition-all"
                              style={{
                                width: `${Math.min(
                                  ((c.started_count - c.submitted_count) / c.invited_count) * 100,
                                  100 - c.completion_rate
                                )}%`,
                              }}
                            />
                          )}
                        </div>
                      </div>
                      <span className={clsx(
                        "text-xs font-semibold w-10",
                        c.completion_rate >= 70
                          ? "text-primary-700"
                          : c.completion_rate >= 40
                          ? "text-accent-700"
                          : "text-red-600"
                      )}>
                        {c.completion_rate}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-3">
                    <span
                      className={clsx(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold",
                        dropoff <= 30
                          ? "bg-primary-100 text-primary-800"
                          : dropoff <= 60
                          ? "bg-accent-100 text-accent-800"
                          : "bg-red-100 text-red-800"
                      )}
                    >
                      {dropoff}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 border-t border-navy-100 flex items-center gap-5 text-[10px] text-navy-400">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-2 rounded-sm bg-primary-500" />
          {t("dropoff.completedSegment")}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-2 rounded-sm bg-accent-300" />
          {t("dropoff.startedSegment")}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-2 rounded-sm bg-navy-100" />
          {t("dropoff.notStartedSegment")}
        </span>
      </div>
    </Card>
  );
}
