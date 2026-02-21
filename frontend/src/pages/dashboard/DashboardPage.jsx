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
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("dashboard.title")}</h1>
          <p className="text-sm text-navy-500 mt-0.5">{t("dashboard.subtitle")}</p>
        </div>
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
            color="primary"
          />
          <KPICard
            label={t("dashboard.candidatesThisMonth")}
            value={summary.kpis.candidates_this_month}
            color="primary"
          />
          <KPICard
            label={t("dashboard.completionRate")}
            value={`${summary.kpis.completion_rate}%`}
            color={summary.kpis.completion_rate >= 70 ? "primary" : "accent"}
          />
          <KPICard
            label={t("dashboard.avgScore")}
            value={summary.kpis.avg_score || "—"}
            color="primary"
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
            <ActivityFeed activities={activities} t={t} />
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
        {t(`dashboard.action.${item.type}`)}
      </span>
    </button>
  );
}

function KPICard({ label, value, color }) {
  const dotColor = color === "accent" ? "bg-accent-400" : "bg-primary-400";
  return (
    <Card className="!p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className={clsx("w-2 h-2 rounded-full", dotColor)} />
        <span className="text-xs font-medium text-navy-500 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold text-navy-900">{value}</p>
    </Card>
  );
}

function PipelineFunnel({ pipeline, t }) {
  const stages = [
    { key: "invited", label: t("dashboard.pipeline.invited"), color: "bg-navy-200" },
    { key: "started", label: t("dashboard.pipeline.started"), color: "bg-blue-300" },
    { key: "awaiting_review", label: t("dashboard.pipeline.awaitingReview"), color: "bg-accent-300" },
    { key: "reviewed", label: t("dashboard.pipeline.reviewed"), color: "bg-primary-300" },
    { key: "shortlisted", label: t("dashboard.pipeline.shortlisted"), color: "bg-primary-500" },
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
            <div className="flex-1 bg-navy-100 rounded-full h-6 overflow-hidden">
              <div
                className={clsx("h-full rounded-full flex items-center justify-end px-2 transition-all", stage.color)}
                style={{ width: `${pct}%`, minWidth: "2rem" }}
              >
                <span className="text-xs font-bold text-navy-800">{val}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ActivityFeed({ activities, t }) {
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
  };

  const actionIcons = {
    "candidate.invited": "text-blue-500",
    "candidate.shortlisted": "text-primary-500",
    "candidate.rejected": "text-red-500",
    "candidate.hold": "text-accent-500",
    "candidate.submitted": "text-primary-600",
    "candidate.erased": "text-navy-400",
    "campaign.created": "text-primary-500",
  };

  return (
    <div className="space-y-3 max-h-64 overflow-y-auto">
      {activities.map((activity, idx) => (
        <div key={idx} className="flex items-start gap-3">
          <div className={clsx("w-2 h-2 mt-1.5 rounded-full shrink-0", actionIcons[activity.action] ? actionIcons[activity.action].replace("text-", "bg-") : "bg-navy-300")} />
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
            <p className="text-xs text-navy-400">
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
      className="cursor-pointer hover:border-primary-300 hover:shadow-md transition-all"
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
