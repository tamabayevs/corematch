import { useState, useEffect, useCallback } from "react";
import { useI18n } from "../../lib/i18n";
import { useNavigate } from "react-router-dom";
import { talentPoolApi } from "../../api/talentPool";
import { campaignsApi } from "../../api/campaigns";

const TIERS = ["all", "gold", "silver", "bronze", "no_tier"];
const DECISIONS = ["all", "shortlisted", "rejected", "on_hold", "pending"];
const PAGE_SIZE = 20;

export default function TalentPoolPage() {
  const { t } = useI18n();
  const navigate = useNavigate();

  const [candidates, setCandidates] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [campaigns, setCampaigns] = useState([]);
  const [savedSearches, setSavedSearches] = useState([]);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [searchName, setSearchName] = useState("");
  const [showSidebar, setShowSidebar] = useState(false);

  const [filters, setFilters] = useState({
    q: "",
    tier: "all",
    decision: "all",
    campaign_id: "",
    score_min: "",
    score_max: "",
    date_from: "",
    date_to: "",
  });

  useEffect(() => {
    loadCampaigns();
    loadSavedSearches();
  }, []);

  useEffect(() => {
    search();
  }, [page]);

  const loadCampaigns = async () => {
    try {
      const { data } = await campaignsApi.list();
      setCampaigns(data.campaigns || []);
    } catch (e) { console.error(e); }
  };

  const loadSavedSearches = async () => {
    try {
      const { data } = await talentPoolApi.listSavedSearches();
      setSavedSearches(data.searches || []);
    } catch (e) { console.error(e); }
  };

  const buildParams = useCallback(() => {
    const params = { page, per_page: PAGE_SIZE };
    if (filters.q) params.q = filters.q;
    if (filters.tier !== "all") params.tier = filters.tier;
    if (filters.decision !== "all") params.decision = filters.decision;
    if (filters.campaign_id) params.campaign_id = filters.campaign_id;
    if (filters.score_min) params.score_min = Number(filters.score_min);
    if (filters.score_max) params.score_max = Number(filters.score_max);
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    return params;
  }, [filters, page]);

  const search = async () => {
    setLoading(true);
    try {
      const { data } = await talentPoolApi.search(buildParams());
      setCandidates(data.candidates || []);
      setTotal(data.total || 0);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    search();
  };

  const handleSaveSearch = async () => {
    try {
      await talentPoolApi.saveSearch({ name: searchName, filters });
      setShowSaveModal(false);
      setSearchName("");
      loadSavedSearches();
    } catch (e) { console.error(e); }
  };

  const applySavedSearch = (saved) => {
    setFilters(saved.filters || {
      q: "", tier: "all", decision: "all", campaign_id: "",
      score_min: "", score_max: "", date_from: "", date_to: "",
    });
    setPage(1);
    setShowSidebar(false);
    // Trigger search on next tick after filters update
    setTimeout(() => search(), 0);
  };

  const handleDeleteSaved = async (id) => {
    try {
      await talentPoolApi.deleteSavedSearch(id);
      loadSavedSearches();
    } catch (e) { console.error(e); }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const tierBadge = (tier) => {
    const colors = {
      gold: "bg-amber-100 text-amber-700",
      silver: "bg-navy-100 text-navy-600",
      bronze: "bg-orange-100 text-orange-700",
    };
    return colors[tier] || "bg-navy-50 text-navy-400";
  };

  const decisionBadge = (decision) => {
    const colors = {
      shortlisted: "bg-primary-100 text-primary-700",
      rejected: "bg-red-100 text-red-700",
      on_hold: "bg-accent-100 text-accent-700",
      pending: "bg-navy-100 text-navy-500",
    };
    return colors[decision] || "bg-navy-50 text-navy-400";
  };

  return (
    <div className="flex gap-6">
      {/* Saved Searches Sidebar (mobile toggle) */}
      {showSidebar && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setShowSidebar(false)}>
          <div className="absolute inset-0 bg-black/30" />
          <div className="absolute start-0 top-0 bottom-0 w-72 bg-white shadow-xl p-4 overflow-y-auto" onClick={e => e.stopPropagation()}>
            <SavedSearchesList
              searches={savedSearches}
              onApply={applySavedSearch}
              onDelete={handleDeleteSaved}
              t={t}
            />
          </div>
        </div>
      )}

      {/* Saved Searches Sidebar (desktop) */}
      <div className="hidden lg:block w-64 shrink-0">
        <SavedSearchesList
          searches={savedSearches}
          onApply={applySavedSearch}
          onDelete={handleDeleteSaved}
          t={t}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-navy-900">{t("talentPool.title")}</h1>
            <p className="text-navy-500 mt-1">{t("talentPool.subtitle")}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowSidebar(true)} className="lg:hidden text-navy-500 hover:text-navy-700 p-2 rounded-lg hover:bg-navy-100">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>
            </button>
            <button onClick={() => setShowSaveModal(true)} className="bg-navy-100 hover:bg-navy-200 text-navy-700 px-3 py-2 rounded-lg text-sm font-medium">
              {t("talentPool.saveSearch")}
            </button>
          </div>
        </div>

        {/* Filters */}
        <form onSubmit={handleSearch} className="bg-white border border-navy-200 rounded-xl p-4 mb-4">
          <div className="flex gap-3 mb-3">
            <input
              type="text"
              value={filters.q}
              onChange={e => setFilters(p => ({ ...p, q: e.target.value }))}
              placeholder={t("talentPool.searchPlaceholder")}
              className="flex-1 border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <button type="submit" className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
              {t("talentPool.search")}
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <div>
              <label className="block text-xs font-medium text-navy-500 mb-1">{t("talentPool.tier")}</label>
              <select value={filters.tier} onChange={e => setFilters(p => ({ ...p, tier: e.target.value }))}
                className="w-full border border-navy-200 rounded-lg px-2 py-1.5 text-sm">
                {TIERS.map(tier => <option key={tier} value={tier}>{tier === "all" ? t("common.all") : t(`talentPool.tiers.${tier}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-navy-500 mb-1">{t("talentPool.decision")}</label>
              <select value={filters.decision} onChange={e => setFilters(p => ({ ...p, decision: e.target.value }))}
                className="w-full border border-navy-200 rounded-lg px-2 py-1.5 text-sm">
                {DECISIONS.map(d => <option key={d} value={d}>{d === "all" ? t("common.all") : t(`talentPool.decisions.${d}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-navy-500 mb-1">{t("talentPool.campaign")}</label>
              <select value={filters.campaign_id} onChange={e => setFilters(p => ({ ...p, campaign_id: e.target.value }))}
                className="w-full border border-navy-200 rounded-lg px-2 py-1.5 text-sm">
                <option value="">{t("common.all")}</option>
                {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-navy-500 mb-1">{t("talentPool.scoreMin")}</label>
              <input type="number" min="0" max="100" value={filters.score_min}
                onChange={e => setFilters(p => ({ ...p, score_min: e.target.value }))}
                className="w-full border border-navy-200 rounded-lg px-2 py-1.5 text-sm" placeholder="0" />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy-500 mb-1">{t("talentPool.scoreMax")}</label>
              <input type="number" min="0" max="100" value={filters.score_max}
                onChange={e => setFilters(p => ({ ...p, score_max: e.target.value }))}
                className="w-full border border-navy-200 rounded-lg px-2 py-1.5 text-sm" placeholder="100" />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy-500 mb-1">{t("talentPool.dateFrom")}</label>
              <input type="date" value={filters.date_from}
                onChange={e => setFilters(p => ({ ...p, date_from: e.target.value }))}
                className="w-full border border-navy-200 rounded-lg px-2 py-1.5 text-sm" />
            </div>
          </div>
        </form>

        {/* Results */}
        {loading ? (
          <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>
        ) : candidates.length === 0 ? (
          <div className="text-center py-16 text-navy-400">
            <svg className="w-12 h-12 mx-auto mb-3 text-navy-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <p className="text-lg font-medium">{t("talentPool.noResults")}</p>
            <p className="text-sm mt-1">{t("talentPool.noResultsDesc")}</p>
          </div>
        ) : (
          <>
            <div className="text-sm text-navy-500 mb-3">
              {t("talentPool.resultCount", { count: total })}
            </div>
            <div className="bg-white border border-navy-200 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-navy-50 border-b border-navy-200">
                  <tr>
                    <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("team.name")}</th>
                    <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("auth.email")}</th>
                    <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("talentPool.campaign")}</th>
                    <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("talentPool.score")}</th>
                    <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("talentPool.tier")}</th>
                    <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("talentPool.decision")}</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-100">
                  {candidates.map((c) => (
                    <tr key={c.id} className="hover:bg-navy-50">
                      <td className="px-4 py-3 text-sm font-medium text-navy-900">{c.full_name || "\u2014"}</td>
                      <td className="px-4 py-3 text-sm text-navy-600">{c.email}</td>
                      <td className="px-4 py-3 text-sm text-navy-600">{c.campaign_name || "\u2014"}</td>
                      <td className="px-4 py-3">
                        <span className="text-sm font-semibold text-navy-900">{c.overall_score != null ? c.overall_score : "\u2014"}</span>
                      </td>
                      <td className="px-4 py-3">
                        {c.tier && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${tierBadge(c.tier)}`}>
                            {t(`talentPool.tiers.${c.tier}`)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${decisionBadge(c.decision || "pending")}`}>
                          {t(`talentPool.decisions.${c.decision || "pending"}`)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-end">
                        <button
                          onClick={() => navigate(`/dashboard/campaigns/${c.campaign_id}/candidates/${c.id}`)}
                          className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                        >
                          {t("common.view")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-navy-500">
                  {t("talentPool.page", { current: page, total: totalPages })}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm border border-navy-200 rounded-lg hover:bg-navy-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {t("common.previous")}
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1.5 text-sm border border-navy-200 rounded-lg hover:bg-navy-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {t("common.next")}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Save Search Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-navy-900 mb-4">{t("talentPool.saveSearch")}</h2>
            <div>
              <label className="block text-sm font-medium text-navy-700 mb-1">{t("talentPool.searchName")}</label>
              <input type="text" value={searchName} onChange={e => setSearchName(e.target.value)}
                placeholder={t("talentPool.searchNamePlaceholder")}
                className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowSaveModal(false)} className="px-4 py-2 text-sm text-navy-600 hover:bg-navy-100 rounded-lg">{t("common.cancel")}</button>
              <button onClick={handleSaveSearch} disabled={!searchName.trim()} className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-40">{t("common.save")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Sub-components ---

function SavedSearchesList({ searches, onApply, onDelete, t }) {
  return (
    <div className="bg-white border border-navy-200 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-navy-900 mb-3">{t("talentPool.savedSearches")}</h3>
      {searches.length === 0 ? (
        <p className="text-xs text-navy-400">{t("talentPool.noSavedSearches")}</p>
      ) : (
        <div className="space-y-2">
          {searches.map((s) => (
            <div key={s.id} className="flex items-center justify-between group">
              <button
                onClick={() => onApply(s)}
                className="text-sm text-navy-700 hover:text-primary-600 font-medium truncate flex-1 text-start"
              >
                {s.name}
              </button>
              <button
                onClick={() => onDelete(s.id)}
                className="text-navy-300 hover:text-red-500 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
