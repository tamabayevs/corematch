import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { formatDate } from "../../lib/formatDate";
import api from "../../api/client";
import { campaignsApi } from "../../api/campaigns";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import ScoreBadge from "../../components/ui/ScoreBadge";
import EmptyState from "../../components/ui/EmptyState";
import clsx from "clsx";

const SORT_OPTIONS = ["score", "name", "date"];

const TIER_VARIANTS = {
  strong_proceed: "teal",
  consider: "amber",
  likely_pass: "red",
};

const DECISION_VARIANTS = {
  shortlisted: "teal",
  rejected: "red",
  hold: "amber",
};

export default function ReviewQueuePage() {
  const { t, locale } = useI18n();
  const navigate = useNavigate();

  const [queue, setQueue] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [unreviewedCount, setUnreviewedCount] = useState(0);

  // Filters
  const [campaignFilter, setCampaignFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [showReviewed, setShowReviewed] = useState(false);
  const [sortBy, setSortBy] = useState("score");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const PER_PAGE = 20;

  // Load campaigns for dropdown
  useEffect(() => {
    const loadCampaigns = async () => {
      try {
        const res = await campaignsApi.list();
        setCampaigns(res.data.campaigns || []);
      } catch {
        // Handle silently
      }
    };
    loadCampaigns();
  }, []);

  // Load review queue when filters change
  const loadQueue = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        reviewed: showReviewed,
        sort: sortBy,
        page,
        per_page: PER_PAGE,
      };
      if (campaignFilter) params.campaign_id = campaignFilter;
      if (tierFilter) params.tier = tierFilter;

      const res = await api.get("/reviews/queue", { params });
      setQueue(res.data.candidates || []);
      setTotalCount(res.data.total || 0);
      setUnreviewedCount(res.data.unreviewed_count || 0);
      setTotalPages(res.data.total_pages || 1);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  }, [campaignFilter, tierFilter, showReviewed, sortBy, page]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [campaignFilter, tierFilter, showReviewed, sortBy]);

  const handleStartSession = () => {
    if (queue.length > 0) {
      navigate(`/dashboard/reviews/${queue[0].id}`);
    }
  };

  // formatDate is now imported from lib/formatDate (locale-aware, Hijri support)

  const tierLabel = (tier) => {
    if (!tier) return null;
    const keyMap = {
      strong_proceed: "strongProceed",
      consider: "consider",
      likely_pass: "likelyPass",
    };
    return t(`candidate.${keyMap[tier] || tier}`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">
            {t("review.queue")}
          </h1>
          <p className="text-sm text-navy-500 mt-0.5">
            {t("review.toReview", { count: unreviewedCount })}
          </p>
        </div>
        <Button onClick={handleStartSession} disabled={queue.length === 0}>
          <svg
            className="w-4 h-4 me-1.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {t("review.startSession")}
        </Button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="!p-4 text-center">
          <p className="text-2xl font-bold text-navy-900">{unreviewedCount}</p>
          <p className="text-sm text-navy-500">{t("review.unreviewed")}</p>
        </Card>
        <Card className="!p-4 text-center">
          <p className="text-2xl font-bold text-navy-900">
            {totalCount - unreviewedCount}
          </p>
          <p className="text-sm text-navy-500">{t("review.reviewed")}</p>
        </Card>
        <Card className="!p-4 text-center">
          <p className="text-2xl font-bold text-navy-900">{totalCount}</p>
          <p className="text-sm text-navy-500">{t("review.totalSubmissions")}</p>
        </Card>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Campaign filter */}
        <select
          className="rounded-lg border border-navy-300 px-3 py-1.5 text-sm bg-white"
          value={campaignFilter}
          onChange={(e) => setCampaignFilter(e.target.value)}
        >
          <option value="">{t("review.allCampaigns")}</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        {/* Tier filter */}
        <select
          className="rounded-lg border border-navy-300 px-3 py-1.5 text-sm bg-white"
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
        >
          <option value="">
            {t("candidate.tier")}: {t("common.all")}
          </option>
          <option value="strong_proceed">
            {t("candidate.strongProceed")}
          </option>
          <option value="consider">{t("candidate.consider")}</option>
          <option value="likely_pass">{t("candidate.likelyPass")}</option>
        </select>

        {/* Sort */}
        <select
          className="rounded-lg border border-navy-300 px-3 py-1.5 text-sm bg-white"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {t(`review.sortBy.${opt}`)}
            </option>
          ))}
        </select>

        {/* Reviewed / Unreviewed toggle */}
        <div className="flex gap-1 bg-navy-100 rounded-lg p-1 ms-auto">
          <button
            onClick={() => setShowReviewed(false)}
            className={clsx(
              "px-3 py-1 rounded-md text-sm font-medium transition-colors",
              !showReviewed
                ? "bg-white text-navy-900 shadow-sm"
                : "text-navy-500 hover:text-navy-700"
            )}
          >
            {t("review.unreviewed")}
          </button>
          <button
            onClick={() => setShowReviewed(true)}
            className={clsx(
              "px-3 py-1 rounded-md text-sm font-medium transition-colors",
              showReviewed
                ? "bg-white text-navy-900 shadow-sm"
                : "text-navy-500 hover:text-navy-700"
            )}
          >
            {t("review.reviewed")}
          </button>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : queue.length === 0 ? (
        <EmptyState
          icon={
            <svg
              className="w-12 h-12"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
          title={t("review.noSubmissions")}
          description={t("review.noSubmissionsDesc")}
        />
      ) : (
        <>
          <Card className="!p-0 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-navy-200 bg-navy-50">
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("auth.fullName")}
                  </th>
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("review.campaign")}
                  </th>
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("candidate.score")}
                  </th>
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("candidate.tier")}
                  </th>
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("candidate.status")}
                  </th>
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("candidate.decision")}
                  </th>
                  <th className="text-start px-4 py-3 text-sm font-medium text-navy-500">
                    {t("review.submittedAt")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-200">
                {queue.map((candidate) => (
                  <tr
                    key={candidate.id}
                    className="hover:bg-navy-50 cursor-pointer transition-colors"
                    onClick={() =>
                      navigate(`/dashboard/reviews/${candidate.id}`)
                    }
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-navy-900">
                          {candidate.full_name}
                        </p>
                        <p className="text-xs text-navy-500">
                          {candidate.email}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-navy-700">
                        {candidate.campaign_name}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {candidate.overall_score != null ? (
                        <ScoreBadge
                          score={candidate.overall_score}
                          tier={candidate.tier}
                        />
                      ) : (
                        <span className="text-sm text-navy-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {candidate.tier ? (
                        <Badge variant={TIER_VARIANTS[candidate.tier]}>
                          {tierLabel(candidate.tier)}
                        </Badge>
                      ) : (
                        <span className="text-sm text-navy-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="teal">
                        {t("candidate.submittedStatus")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {candidate.hr_decision ? (
                        <Badge
                          variant={DECISION_VARIANTS[candidate.hr_decision]}
                        >
                          {t(`candidate.${candidate.hr_decision}`)}
                        </Badge>
                      ) : (
                        <span className="text-sm text-navy-400">
                          {t("candidate.noDecision")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-navy-500">
                        {formatDate(candidate.submitted_at, locale)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-navy-500">
                {t("review.page", { current: page, total: totalPages })}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  {t("review.previous")}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  {t("review.next")}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
