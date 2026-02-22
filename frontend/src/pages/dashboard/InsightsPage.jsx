import { useEffect, useState } from "react";
import { useI18n } from "../../lib/i18n";
import { campaignsApi } from "../../api/campaigns";
import api from "../../api/client";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import clsx from "clsx";

export default function InsightsPage() {
  const { t, locale } = useI18n();

  // Filters
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const [campaignsList, setCampaignsList] = useState([]);

  // Data
  const [summary, setSummary] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [scoreDist, setScoreDist] = useState(null);
  const [byCampaign, setByCampaign] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load campaigns for dropdown
  useEffect(() => {
    campaignsApi.list().then((res) => {
      setCampaignsList(res.data.campaigns || []);
    }).catch(() => {});
  }, []);

  // Load insights data whenever filters change
  useEffect(() => {
    loadInsights();
  }, [dateFrom, dateTo, campaignId]);

  const buildParams = () => {
    const params = {};
    if (dateFrom) params.from = dateFrom;
    if (dateTo) params.to = dateTo;
    if (campaignId) params.campaign_id = campaignId;
    return { params };
  };

  const loadInsights = async () => {
    setLoading(true);
    const config = buildParams();
    try {
      const [summaryRes, funnelRes, scoreRes, campaignRes] = await Promise.all([
        api.get("/insights/summary", config),
        api.get("/insights/funnel", config),
        api.get("/insights/score-distribution", config),
        api.get("/insights/by-campaign", config),
      ]);
      setSummary(summaryRes.data);
      setFunnel(funnelRes.data);
      setScoreDist(scoreRes.data);
      setByCampaign(campaignRes.data);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header + Filters */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("insights.title")}</h1>
          <p className="text-sm text-navy-500 mt-0.5">{t("insights.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <FilterInput
            label={t("insights.dateFrom")}
            type="date"
            value={dateFrom}
            onChange={setDateFrom}
            lang={locale === "ar" ? "ar" : "en"}
          />
          <FilterInput
            label={t("insights.dateTo")}
            type="date"
            value={dateTo}
            onChange={setDateTo}
            lang={locale === "ar" ? "ar" : "en"}
          />
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
          {/* KPI Row */}
          {summary && <KPIRow summary={summary} t={t} />}

          {/* Funnel + Score Distribution side-by-side */}
          <div className="grid lg:grid-cols-2 gap-4">
            {funnel && <FunnelChart funnel={funnel} t={t} />}
            {scoreDist && <ScoreDistribution scoreDist={scoreDist} t={t} />}
          </div>

          {/* Campaign Comparison Table */}
          {byCampaign && <CampaignComparison byCampaign={byCampaign} t={t} />}
        </>
      )}
    </div>
  );
}

// ─── Filter Input ──────────────────────────────────────────────

function FilterInput({ label, type, value, onChange, lang }) {
  return (
    <div className="flex flex-col">
      <label className="text-xs font-medium text-navy-500 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        lang={lang}
        className="h-9 rounded-lg border border-navy-200 bg-white px-3 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
      />
    </div>
  );
}

// ─── KPI Row ───────────────────────────────────────────────────

function KPIRow({ summary, t }) {
  const kpis = [
    {
      label: t("insights.timeToSubmit"),
      value: summary.time_to_submit_avg > 0
        ? `${summary.time_to_submit_avg} ${t("insights.hours")}`
        : "--",
      color: "primary",
    },
    {
      label: t("insights.completionRate"),
      value: `${summary.completion_rate}%`,
      color: summary.completion_rate >= 70 ? "primary" : "accent",
    },
    {
      label: t("insights.passRate"),
      value: `${summary.pass_rate}%`,
      color: summary.pass_rate >= 50 ? "primary" : "accent",
    },
    {
      label: t("insights.avgScore"),
      value: summary.avg_ai_score > 0 ? summary.avg_ai_score : "--",
      color: "primary",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {kpis.map((kpi, idx) => (
        <Card key={idx} className="!p-4">
          <div className="flex items-center gap-2 mb-2">
            <div
              className={clsx(
                "w-2 h-2 rounded-full",
                kpi.color === "accent" ? "bg-accent-400" : "bg-primary-400"
              )}
            />
            <span className="text-xs font-medium text-navy-500 uppercase tracking-wide">
              {kpi.label}
            </span>
          </div>
          <p className="text-2xl font-bold text-navy-900">{kpi.value}</p>
        </Card>
      ))}
    </div>
  );
}

// ─── Pipeline Funnel ───────────────────────────────────────────

function FunnelChart({ funnel, t }) {
  const stages = funnel.stages || [];
  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  const stageLabels = {
    invited: t("dashboard.pipeline.invited"),
    started: t("dashboard.pipeline.started"),
    submitted: t("dashboard.submitted"),
    reviewed: t("dashboard.pipeline.reviewed"),
    shortlisted: t("dashboard.pipeline.shortlisted"),
    rejected: t("candidate.rejected"),
  };

  const stageColors = {
    invited: "bg-navy-300",
    started: "bg-blue-300",
    submitted: "bg-accent-300",
    reviewed: "bg-primary-300",
    shortlisted: "bg-primary-500",
    rejected: "bg-red-400",
  };

  return (
    <Card>
      <h3 className="font-semibold text-navy-900 mb-5">{t("insights.funnel")}</h3>
      <div className="space-y-3">
        {stages.map((stage, idx) => {
          const pct = Math.max((stage.count / maxCount) * 100, 4);
          const prev = idx > 0 ? stages[idx - 1] : null;
          const convRate =
            prev && prev.count > 0
              ? Math.round((stage.count / prev.count) * 100)
              : null;

          return (
            <div key={stage.name}>
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-navy-500 w-24 text-end shrink-0">
                  {stageLabels[stage.name] || stage.name}
                </span>
                <div className="flex-1 bg-navy-100 rounded-full h-7 overflow-hidden">
                  <div
                    className={clsx(
                      "h-full rounded-full flex items-center justify-end px-2.5 transition-all",
                      stageColors[stage.name] || "bg-navy-200"
                    )}
                    style={{ width: `${pct}%`, minWidth: "2.5rem" }}
                  >
                    <span className="text-xs font-bold text-navy-800">
                      {stage.count}
                    </span>
                  </div>
                </div>
                {convRate !== null && (
                  <span className="text-[10px] text-navy-400 w-12 shrink-0">
                    {convRate}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-navy-400 mt-3 text-end">
        {t("insights.conversionRate")}
      </p>
    </Card>
  );
}

// ─── Score Distribution ────────────────────────────────────────

function ScoreDistribution({ scoreDist, t }) {
  const buckets = scoreDist.buckets || [];
  const maxCount = Math.max(...buckets.map((b) => b.count), 1);
  const totalCount = buckets.reduce((sum, b) => sum + b.count, 0);

  const barColors = [
    "bg-red-400",
    "bg-accent-400",
    "bg-yellow-400",
    "bg-primary-300",
    "bg-primary-500",
  ];

  return (
    <Card>
      <h3 className="font-semibold text-navy-900 mb-5">
        {t("insights.scoreDistribution")}
      </h3>
      {totalCount === 0 ? (
        <p className="text-sm text-navy-400 text-center py-8">
          {t("insights.noData")}
        </p>
      ) : (
        <div className="flex items-end justify-around gap-2" style={{ height: "180px" }}>
          {buckets.map((bucket, idx) => {
            const heightPct = maxCount > 0 ? (bucket.count / maxCount) * 100 : 0;
            return (
              <div key={bucket.range} className="flex flex-col items-center flex-1 h-full justify-end">
                <span className="text-xs font-bold text-navy-700 mb-1">
                  {bucket.count}
                </span>
                <div
                  className={clsx(
                    "w-full max-w-[48px] rounded-t-md transition-all",
                    barColors[idx] || "bg-navy-300"
                  )}
                  style={{
                    height: `${Math.max(heightPct, 3)}%`,
                    minHeight: "4px",
                  }}
                />
                <span className="text-[10px] text-navy-500 mt-1.5 font-medium">
                  {bucket.range}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

// ─── Campaign Comparison Table ─────────────────────────────────

function CampaignComparison({ byCampaign, t }) {
  const campaigns = byCampaign.campaigns || [];

  if (campaigns.length === 0) {
    return (
      <Card>
        <h3 className="font-semibold text-navy-900 mb-4">{t("insights.byCampaign")}</h3>
        <p className="text-sm text-navy-400 text-center py-8">
          {t("insights.noData")}
        </p>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden !p-0">
      <div className="p-6 pb-4">
        <h3 className="font-semibold text-navy-900">{t("insights.byCampaign")}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-t border-b border-navy-200 bg-navy-50">
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("campaign.name")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("dashboard.candidates")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("dashboard.submitted")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider min-w-[180px]">
                {t("insights.completionRate")}
              </th>
              <th className="text-start px-6 py-3 font-medium text-navy-500 text-xs uppercase tracking-wider">
                {t("insights.avgScore")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-100">
            {campaigns.map((c) => (
              <tr key={c.campaign_id} className="hover:bg-navy-50 transition-colors">
                <td className="px-6 py-3 font-medium text-navy-800 truncate max-w-[200px]">
                  {c.name}
                </td>
                <td className="px-6 py-3 text-navy-600">{c.candidate_count}</td>
                <td className="px-6 py-3 text-navy-600">{c.submitted_count}</td>
                <td className="px-6 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 bg-navy-100 rounded-full h-2 max-w-[100px]">
                      <div
                        className={clsx(
                          "h-full rounded-full transition-all",
                          c.completion_rate >= 70
                            ? "bg-primary-500"
                            : c.completion_rate >= 40
                            ? "bg-accent-400"
                            : "bg-red-400"
                        )}
                        style={{
                          width: `${Math.min(c.completion_rate, 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium text-navy-600 w-10">
                      {c.completion_rate}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-3">
                  {c.avg_score != null ? (
                    <span
                      className={clsx(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold",
                        c.avg_score >= 70
                          ? "bg-primary-100 text-primary-800"
                          : c.avg_score >= 40
                          ? "bg-accent-100 text-accent-800"
                          : "bg-red-100 text-red-800"
                      )}
                    >
                      {c.avg_score}
                    </span>
                  ) : (
                    <span className="text-navy-400">--</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
