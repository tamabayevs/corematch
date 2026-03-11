import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { formatRelativeTime as sharedFormatRelativeTime } from "../../lib/formatDate";
import { dashboardApi } from "../../api/dashboard";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import EmptyState from "../../components/ui/EmptyState";
import OnboardingChecklist from "../../components/OnboardingChecklist";
import clsx from "clsx";

const STATUS_FILTERS = ["all", "active", "closed", "archived"];

export default function DashboardPage() {
  const { t, locale } = useI18n();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [activities, setActivities] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    loadCampaigns();
  }, [filter]);

  const loadDashboard = async () => {
    try {
      const [summaryRes, activityRes] = await Promise.all([
        dashboardApi.summary(),
        dashboardApi.activity(8),
      ]);
      setSummary(summaryRes.data);
      setActivities(activityRes.data.activities);
    } catch {
      // Handle silently
    }
  };

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const status = filter === "all" ? undefined : filter;
      const res = await dashboardApi.campaigns(status);
      setCampaigns(res.data.campaigns);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status) => {
    const variants = { active: "teal", closed: "red", archived: "gray" };
    return <Badge variant={variants[status] || "gray"}>{t(`dashboard.${status}`)}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-navy-500">{t("dashboard.subtitle")}</p>
        <Button onClick={() => navigate("/dashboard/campaigns/new")}>
          {t("dashboard.newCampaign")}
        </Button>
      </div>

      {/* Action Items */}
      {summary?.action_items?.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {summary.action_items.map((item, idx) => (
            <ActionItemCard key={idx} item={item} t={t} navigate={navigate} />
          ))}
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            label={t("dashboard.activeCampaigns")}
            value={summary.kpis.active_campaigns}
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />}
            iconColor="bg-primary-50 text-primary-600"
          />
          <KPICard
            label={t("dashboard.candidatesThisMonth")}
            value={summary.kpis.candidates_this_month}
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />}
            iconColor="bg-blue-50 text-blue-600"
          />
          <KPICard
            label={t("dashboard.completionRate")}
            value={`${summary.kpis.completion_rate}%`}
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />}
            iconColor={summary.kpis.completion_rate >= 70 ? "bg-emerald-50 text-emerald-600" : "bg-accent-50 text-accent-600"}
          />
          <KPICard
            label={t("dashboard.avgScore")}
            value={summary.kpis.avg_score || "—"}
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />}
            iconColor="bg-purple-50 text-purple-600"
          />
        </div>
      )}

      {/* Pipeline Overview + Activity Feed */}
      {summary && (
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Pipeline */}
          <Card className="lg:col-span-2">
            <h3 className="font-semibold text-navy-900 mb-4">{t("dashboard.pipelineOverview")}</h3>
            <PipelineFunnel pipeline={summary.pipeline} t={t} />
          </Card>

          {/* Activity Feed */}
          <Card>
            <h3 className="font-semibold text-navy-900 mb-4">{t("dashboard.recentActivity")}</h3>
            <ActivityFeed activities={activities} t={t} locale={locale} />
          </Card>
        </div>
      )}

      {/* Campaigns Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-navy-900">{t("dashboard.yourCampaigns")}</h2>
          <div className="flex gap-1 bg-navy-100 rounded-lg p-1">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={clsx(
                  "px-3 py-1 rounded-md text-sm font-medium transition-colors",
                  filter === s
                    ? "bg-white text-navy-900 shadow-sm"
                    : "text-navy-500 hover:text-navy-700"
                )}
              >
                {s === "all" ? t("common.all") : t(`dashboard.${s}`)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : campaigns.length === 0 && filter === "all" ? (
          <OnboardingChecklist campaigns={campaigns} summary={summary} />
        ) : campaigns.length === 0 ? (
          <EmptyState
            icon={
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            }
            title={t("dashboard.noCampaigns")}
            description={t("dashboard.noCampaignsDesc")}
            actionLabel={t("dashboard.newCampaign")}
            onAction={() => navigate("/dashboard/campaigns/new")}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {campaigns.map((campaign) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                statusBadge={statusBadge}
                navigate={navigate}
                t={t}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────

function ActionItemCard({ item, t, navigate }) {
  const configs = {
    new_submissions: {
      icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z",
      color: "bg-primary-50 border-primary-200 text-primary-700",
      iconColor: "text-primary-500",
    },
    overdue_decisions: {
      icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
      color: "bg-accent-50 border-accent-200 text-accent-700",
      iconColor: "text-accent-500",
    },
    not_started: {
      icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z",
      color: "bg-navy-50 border-navy-200 text-navy-600",
      iconColor: "text-navy-400",
    },
    expiring_invites: {
      icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
      color: "bg-red-50 border-red-200 text-red-700",
      iconColor: "text-red-500",
    },
  };

  const config = configs[item.type] || configs.not_started;

  return (
    <button
      onClick={() => navigate(item.link)}
      className={clsx(
        "flex items-center gap-3 px-4 py-3 rounded-xl border transition-all hover:shadow-sm",
        config.color
      )}
    >
      <svg className={clsx("w-5 h-5 shrink-0", config.iconColor)} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
      </svg>
      <span className="text-sm font-medium">
        <span className="font-bold">{item.count}</span>{" "}
        {item.count === 1 && t(`dashboard.action.${item.type}_one`)
          ? t(`dashboard.action.${item.type}_one`)
          : t(`dashboard.action.${item.type}`)}
      </span>
    </button>
  );
}

function KPICard({ label, value, icon, iconColor }) {
  return (
    <Card className="!p-4">
      <div className="flex items-center gap-3">
        <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0", iconColor)}>
          <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {icon}
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-navy-500 uppercase tracking-wide truncate">{label}</p>
          <p className="text-xl font-bold text-navy-900">{value}</p>
        </div>
      </div>
    </Card>
  );
}

function PipelineFunnel({ pipeline, t }) {
  const stages = [
    { key: "invited", label: t("dashboard.pipeline.invited"), from: "from-navy-300", to: "to-navy-200" },
    { key: "started", label: t("dashboard.pipeline.started"), from: "from-blue-400", to: "to-blue-300" },
    { key: "awaiting_review", label: t("dashboard.pipeline.awaitingReview"), from: "from-accent-400", to: "to-accent-300" },
    { key: "reviewed", label: t("dashboard.pipeline.reviewed"), from: "from-primary-400", to: "to-primary-300" },
    { key: "shortlisted", label: t("dashboard.pipeline.shortlisted"), from: "from-primary-600", to: "to-primary-500" },
  ];

  const maxVal = Math.max(...stages.map((s) => pipeline[s.key] || 0), 1);

  return (
    <div className="space-y-3">
      {stages.map((stage) => {
        const val = pipeline[stage.key] || 0;
        const pct = Math.max((val / maxVal) * 100, 4);
        return (
          <div key={stage.key} className="flex items-center gap-3">
            <span className="text-xs font-medium text-navy-500 w-28 text-end shrink-0">
              {stage.label}
            </span>
            <div className="flex-1 bg-navy-100 rounded-full h-7 overflow-hidden">
              <div
                className={clsx("h-full rounded-full flex items-center justify-between px-3 bg-gradient-to-r transition-all", stage.from, stage.to)}
                style={{ width: `${pct}%`, minWidth: "3rem" }}
              >
                <span className="text-xs font-bold text-white">{val}</span>
                <span className="text-[10px] font-medium text-white/70">{Math.round((val / maxVal) * 100)}%</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ActivityFeed({ activities, t, locale }) {
  if (!activities.length) {
    return <p className="text-sm text-navy-400">{t("dashboard.noActivity")}</p>;
  }

  const actionLabels = {
    "candidate.invited": t("dashboard.activity.invited"),
    "candidate.shortlisted": t("dashboard.activity.shortlisted"),
    "candidate.rejected": t("dashboard.activity.rejected"),
    "candidate.hold": t("dashboard.activity.hold"),
    "candidate.erased": t("dashboard.activity.erased"),
    "candidate.submitted": t("dashboard.activity.submitted"),
    "campaign.created": t("dashboard.activity.campaignCreated"),
    "comment.created": t("dashboard.activity.commentCreated"),
  };

  const actionIcons = {
    "candidate.invited": "text-blue-500",
    "candidate.shortlisted": "text-primary-500",
    "candidate.rejected": "text-red-500",
    "candidate.hold": "text-accent-500",
    "candidate.submitted": "text-primary-600",
    "candidate.erased": "text-navy-400",
    "campaign.created": "text-primary-500",
    "comment.created": "text-blue-400",
  };

  return (
    <div className="max-h-64 overflow-y-auto divide-y divide-navy-100">
      {activities.map((activity, idx) => (
        <div key={idx} className="flex items-start gap-3 py-3 first:pt-0">
          <div className={clsx("w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold text-white mt-0.5",
            actionIcons[activity.action] ? actionIcons[activity.action].replace("text-", "bg-") : "bg-navy-300"
          )}>
            {(activity.metadata?.candidate_name?.[0] || activity.metadata?.email?.[0] || "?").toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-navy-700">
              {actionLabels[activity.action] || activity.action}
              {activity.metadata?.email && (
                <span className="font-medium"> {activity.metadata.email}</span>
              )}
              {activity.metadata?.candidate_name && (
                <span className="font-medium"> {activity.metadata.candidate_name}</span>
              )}
            </p>
            <p className="text-xs text-navy-400 mt-0.5">
              {sharedFormatRelativeTime(activity.created_at, locale)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function CampaignCard({ campaign, statusBadge, navigate, t }) {
  return (
    <Card
      hoverable
      onClick={() => navigate(`/dashboard/campaigns/${campaign.id}`)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-navy-900 truncate">{campaign.name}</h3>
          <p className="text-sm text-navy-400 truncate">{campaign.job_title}</p>
        </div>
        {statusBadge(campaign.status)}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-sm text-navy-500">
        <span>{t("dashboard.candidates")}: {campaign.total_candidates || 0}</span>
        <span>{t("dashboard.submitted")}: {campaign.submitted_count || 0}</span>
      </div>

      {/* Completion bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-navy-400 mb-1">
          <span>{t("dashboard.completionRate")}</span>
          <span className="font-medium text-navy-600">{campaign.completion_rate}%</span>
        </div>
        <div className="w-full bg-navy-100 rounded-full h-1.5">
          <div
            className={clsx(
              "h-full rounded-full transition-all",
              campaign.completion_rate >= 70 ? "bg-primary-500" : campaign.completion_rate >= 40 ? "bg-accent-400" : "bg-red-400"
            )}
            style={{ width: `${Math.min(campaign.completion_rate, 100)}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between mt-3">
        <p className="text-xs text-navy-400">
          {t("campaign.questionCount", { count: campaign.question_count || 0 })}
        </p>
        {campaign.avg_score && (
          <span className="text-xs font-medium text-primary-600">
            {t("dashboard.avgScoreLabel")}: {campaign.avg_score}
          </span>
        )}
      </div>
    </Card>
  );
}

// ─── Helpers ───────────────────────────────────────────────────

// formatRelativeTime is now imported from lib/formatDate (locale-aware, Hijri support)
