import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import calibrationAPI from "../../api/calibration";
import api from "../../api/client";

export default function CalibrationPage() {
  const { t } = useI18n();
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState("");
  const [data, setData] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch campaigns for dropdown
  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        const res = await api.get("/campaigns");
        setCampaigns(res.data.campaigns || []);
      } catch {}
    };
    fetchCampaigns();
  }, []);

  // Fetch calibration data when campaign selected
  useEffect(() => {
    if (!selectedCampaign) { setData(null); return; }
    const fetch = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await calibrationAPI.getOverview(selectedCampaign);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.error || "Failed to load calibration data");
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [selectedCampaign]);

  const handleViewDetail = async (candidateId) => {
    try {
      const res = await calibrationAPI.getCandidateDetail(selectedCampaign, candidateId);
      setDetail(res.data);
    } catch {}
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-navy-900">{t("calibration.title")}</h1>
        <p className="text-navy-500 mt-1">{t("calibration.subtitle")}</p>
      </div>

      {/* Campaign selector */}
      <div className="bg-white rounded-xl border border-navy-200 p-6">
        <label className="block text-sm font-medium text-navy-700 mb-2">
          {t("calibration.selectCampaign")}
        </label>
        <select
          value={selectedCampaign}
          onChange={(e) => { setSelectedCampaign(e.target.value); setDetail(null); }}
          className="w-full max-w-md px-3 py-2 border border-navy-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="">{t("calibration.chooseCampaign")}</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>{c.name} — {c.job_title}</option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="text-center py-12 text-navy-400">{t("common.loading")}</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600 text-sm">{error}</div>
      )}

      {data && !loading && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl border border-navy-200 p-6">
              <p className="text-sm font-medium text-navy-500">{t("calibration.totalCandidates")}</p>
              <p className="text-3xl font-bold text-navy-900 mt-1">{data.total_candidates}</p>
            </div>
            <div className="bg-white rounded-xl border border-navy-200 p-6">
              <p className="text-sm font-medium text-navy-500">{t("calibration.withEvaluations")}</p>
              <p className="text-3xl font-bold text-primary-600 mt-1">{data.total_with_evaluations}</p>
            </div>
            <div className="bg-white rounded-xl border border-navy-200 p-6">
              <p className="text-sm font-medium text-navy-500">{t("calibration.avgDisagreement")}</p>
              <p className="text-3xl font-bold mt-1" style={{ color: data.avg_disagreement > 1 ? '#ef4444' : data.avg_disagreement > 0.5 ? '#f59e0b' : '#10b981' }}>
                {data.avg_disagreement}
              </p>
            </div>
          </div>

          {/* Candidate calibration table */}
          <div className="bg-white rounded-xl border border-navy-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-navy-100">
              <h2 className="text-lg font-semibold text-navy-900">{t("calibration.reviewerComparison")}</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy-50 text-navy-600">
                    <th className="text-start px-6 py-3 font-medium">{t("calibration.candidate")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("calibration.aiScore")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("calibration.humanAvg")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("calibration.evaluations")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("calibration.disagreement")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("calibration.reviewers")}</th>
                    <th className="px-6 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.candidates.map((c) => (
                    <tr key={c.id} className="border-t border-navy-100 hover:bg-navy-50">
                      <td className="px-6 py-3 font-medium text-navy-900">{c.full_name}</td>
                      <td className="px-6 py-3 text-navy-600">
                        {c.ai_score != null ? c.ai_score.toFixed(1) : "—"}
                      </td>
                      <td className="px-6 py-3 text-navy-600">
                        {c.avg_human_rating != null ? c.avg_human_rating.toFixed(1) + "/5" : "—"}
                      </td>
                      <td className="px-6 py-3 text-navy-600">{c.evaluation_count}</td>
                      <td className="px-6 py-3">
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor: c.disagreement_score > 1 ? '#fef2f2' : c.disagreement_score > 0.5 ? '#fffbeb' : '#ecfdf5',
                            color: c.disagreement_score > 1 ? '#dc2626' : c.disagreement_score > 0.5 ? '#d97706' : '#059669',
                          }}
                        >
                          {c.disagreement_score}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-navy-500 text-xs">
                        {c.evaluations.map((e) => e.reviewer_name).join(", ") || "—"}
                      </td>
                      <td className="px-6 py-3">
                        {c.evaluation_count >= 2 && (
                          <button
                            onClick={() => handleViewDetail(c.id)}
                            className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                          >
                            {t("calibration.viewDetail")}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {data.candidates.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center text-navy-400">
                        {t("calibration.noCandidates")}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 bg-navy-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[80vh] overflow-y-auto">
            <div className="p-6 border-b border-navy-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-navy-900">
                  {detail.candidate.full_name}
                </h2>
                <p className="text-sm text-navy-500 mt-0.5">
                  AI: {detail.candidate.ai_score != null ? detail.candidate.ai_score.toFixed(1) : "—"} · {detail.candidate.tier || "—"}
                </p>
              </div>
              <button onClick={() => setDetail(null)} className="text-navy-400 hover:text-navy-600 text-xl">×</button>
            </div>

            <div className="p-6 space-y-6">
              {/* Side-by-side reviewer ratings */}
              <div>
                <h3 className="text-sm font-semibold text-navy-700 mb-3">{t("calibration.sideBysSide")}</h3>
                <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(detail.evaluations.length, 3)}, 1fr)` }}>
                  {detail.evaluations.map((ev) => (
                    <div key={ev.id} className="bg-navy-50 rounded-lg p-4">
                      <p className="font-medium text-navy-900 text-sm">{ev.reviewer_name}</p>
                      <p className="text-xs text-navy-500 mt-0.5">
                        Overall: <span className="font-bold text-primary-600">{ev.overall_rating}/5</span>
                      </p>
                      {ev.notes && (
                        <p className="text-xs text-navy-600 mt-2 italic">"{ev.notes}"</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Per-competency comparison */}
              {detail.competency_stats.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-navy-700 mb-3">{t("calibration.competencyBreakdown")}</h3>
                  <div className="space-y-3">
                    {detail.competency_stats.map((comp) => (
                      <div
                        key={comp.competency}
                        className={`p-4 rounded-lg border ${comp.has_disagreement ? 'border-red-200 bg-red-50' : 'border-navy-200 bg-white'}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-navy-900 text-sm">{comp.competency}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-navy-500">Avg: {comp.avg}/5</span>
                            {comp.has_disagreement && (
                              <span className="text-xs text-red-600 font-medium">{t("calibration.highDisagreement")}</span>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-4">
                          {comp.scores.map((s, i) => (
                            <div key={i} className="flex items-center gap-1.5">
                              <span className="text-xs text-navy-500">{s.reviewer}:</span>
                              <div className="flex gap-0.5">
                                {[1, 2, 3, 4, 5].map((star) => (
                                  <span
                                    key={star}
                                    className={`w-4 h-4 rounded-full text-[10px] flex items-center justify-center ${
                                      star <= (s.score || 0)
                                        ? 'bg-primary-500 text-white'
                                        : 'bg-navy-200 text-navy-400'
                                    }`}
                                  >
                                    {star}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
