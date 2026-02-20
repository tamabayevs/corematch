import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { campaignsApi } from "../../api/campaigns";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import EmptyState from "../../components/ui/EmptyState";
import clsx from "clsx";

const STATUS_FILTERS = ["all", "active", "closed", "archived"];

export default function DashboardPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    loadCampaigns();
  }, [filter]);

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const status = filter === "all" ? undefined : filter;
      const res = await campaignsApi.list(status);
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
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-navy-900">{t("dashboard.title")}</h1>
        <Button onClick={() => navigate("/dashboard/campaigns/new")}>
          {t("dashboard.newCampaign")}
        </Button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 bg-navy-100 rounded-lg p-1 w-fit">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={clsx(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
              filter === s
                ? "bg-white text-navy-900 shadow-sm"
                : "text-navy-500 hover:text-navy-700"
            )}
          >
            {s === "all" ? t("common.all") : t(`dashboard.${s}`)}
          </button>
        ))}
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
            <Card
              key={campaign.id}
              className="cursor-pointer hover:border-primary-300 hover:shadow-md transition-all"
              onClick={() => navigate(`/dashboard/campaigns/${campaign.id}`)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-navy-900 truncate">
                    {campaign.name}
                  </h3>
                  <p className="text-sm text-navy-400 truncate">{campaign.job_title}</p>
                </div>
                {statusBadge(campaign.status)}
              </div>

              <div className="flex items-center gap-4 text-sm text-navy-500">
                <span>
                  {t("dashboard.candidates")}: {campaign.candidate_count || 0}
                </span>
                <span>
                  {t("dashboard.submitted")}: {campaign.submitted_count || 0}
                </span>
              </div>

              <p className="text-xs text-navy-400 mt-3">
                {t("campaign.questionCount", { count: campaign.questions?.length || 0 })}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
