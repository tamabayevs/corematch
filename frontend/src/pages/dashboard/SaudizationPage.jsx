import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import saudizationAPI from "../../api/saudization";

export default function SaudizationPage() {
  const { t } = useI18n();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [quotaForm, setQuotaForm] = useState({ category: "", target_percentage: "", notes: "" });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await saudizationAPI.dashboard({});
      setData(res.data);
    } catch {} finally { setLoading(false); }
  };

  const handleCreateQuota = async () => {
    try {
      await saudizationAPI.createQuota({
        category: quotaForm.category,
        target_percentage: parseFloat(quotaForm.target_percentage),
        notes: quotaForm.notes || null,
      });
      setShowQuotaModal(false);
      setQuotaForm({ category: "", target_percentage: "", notes: "" });
      fetchData();
    } catch {}
  };

  const handleDeleteQuota = async (id) => {
    try {
      await saudizationAPI.deleteQuota(id);
      fetchData();
    } catch {}
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("saudization.title")}</h1>
          <p className="text-navy-500 mt-1">{t("saudization.subtitle")}</p>
        </div>
        <button
          onClick={() => setShowQuotaModal(true)}
          className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {t("saudization.addQuota")}
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-navy-400">{t("common.loading")}</div>
      ) : data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-navy-200 p-5">
              <p className="text-sm font-medium text-navy-500">{t("saudization.totalCandidates")}</p>
              <p className="text-3xl font-bold text-navy-900 mt-1">{data.summary.total_candidates}</p>
            </div>
            <div className="bg-white rounded-xl border border-navy-200 p-5">
              <p className="text-sm font-medium text-navy-500">{t("saudization.saudiCount")}</p>
              <p className="text-3xl font-bold text-green-600 mt-1">{data.summary.saudi_count}</p>
            </div>
            <div className="bg-white rounded-xl border border-navy-200 p-5">
              <p className="text-sm font-medium text-navy-500">{t("saudization.nonSaudi")}</p>
              <p className="text-3xl font-bold text-navy-600 mt-1">{data.summary.non_saudi_count}</p>
            </div>
            <div className="bg-white rounded-xl border border-navy-200 p-5">
              <p className="text-sm font-medium text-navy-500">{t("saudization.saudiPercentage")}</p>
              <p className="text-3xl font-bold text-primary-600 mt-1">{data.summary.saudi_percentage}%</p>
            </div>
          </div>

          {/* Quotas */}
          {data.quotas.length > 0 && (
            <div className="bg-white rounded-xl border border-navy-200 p-6">
              <h2 className="text-lg font-semibold text-navy-900 mb-4">{t("saudization.quotaTargets")}</h2>
              <div className="space-y-4">
                {data.quotas.map((q) => (
                  <div key={q.id} className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-navy-700">{q.category}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-bold ${q.is_compliant ? 'text-green-600' : 'text-red-600'}`}>
                            {q.current_percentage}% / {q.target_percentage}%
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            q.is_compliant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {q.is_compliant ? t("saudization.compliant") : t("saudization.nonCompliant")}
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-navy-100 rounded-full h-3 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.min(q.current_percentage, 100)}%`,
                            backgroundColor: q.is_compliant ? '#059669' : '#dc2626',
                          }}
                        />
                      </div>
                      {q.notes && <p className="text-xs text-navy-500 mt-1">{q.notes}</p>}
                    </div>
                    <button onClick={() => handleDeleteQuota(q.id)} className="text-red-400 hover:text-red-600 text-sm">×</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Nationality breakdown */}
          <div className="bg-white rounded-xl border border-navy-200 p-6">
            <h2 className="text-lg font-semibold text-navy-900 mb-4">{t("saudization.nationalityBreakdown")}</h2>
            <div className="space-y-3">
              {data.nationality_breakdown.map((n) => (
                <div key={n.nationality} className="flex items-center gap-4">
                  <span className="w-40 text-sm font-medium text-navy-700 truncate">{n.nationality}</span>
                  <div className="flex-1 bg-navy-100 rounded-full h-5 overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full flex items-center px-2 transition-all"
                      style={{ width: `${Math.max(n.percentage, 3)}%` }}
                    >
                      {n.percentage >= 10 && (
                        <span className="text-[10px] text-white font-bold">{n.count}</span>
                      )}
                    </div>
                  </div>
                  <span className="w-20 text-sm text-navy-500 text-end">{n.percentage}%</span>
                  <span className="w-16 text-xs text-navy-400 text-end">
                    {n.avg_score ? `Avg: ${n.avg_score}` : ""}
                  </span>
                </div>
              ))}
              {data.nationality_breakdown.length === 0 && (
                <p className="text-center py-8 text-navy-400">{t("saudization.noData")}</p>
              )}
            </div>
          </div>

          {/* Per-campaign */}
          {data.per_campaign.length > 0 && (
            <div className="bg-white rounded-xl border border-navy-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-navy-100">
                <h2 className="text-lg font-semibold text-navy-900">{t("saudization.perCampaign")}</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy-50 text-navy-600">
                    <th className="text-start px-6 py-3 font-medium">{t("saudization.campaign")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("saudization.total")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("saudization.saudiCount")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("saudization.saudiPct")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("saudization.shortlisted")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.per_campaign.map((c) => (
                    <tr key={c.id} className="border-t border-navy-100">
                      <td className="px-6 py-3">
                        <p className="font-medium text-navy-900">{c.name}</p>
                        <p className="text-xs text-navy-500">{c.job_title}</p>
                      </td>
                      <td className="px-6 py-3 text-navy-600">{c.total}</td>
                      <td className="px-6 py-3 text-navy-600">{c.saudi_count}</td>
                      <td className="px-6 py-3">
                        <span className={`text-sm font-medium ${c.saudi_percentage >= 50 ? 'text-green-600' : 'text-amber-600'}`}>
                          {c.saudi_percentage}%
                        </span>
                      </td>
                      <td className="px-6 py-3 text-navy-600">{c.shortlisted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Quota modal */}
      {showQuotaModal && (
        <div className="fixed inset-0 bg-navy-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="p-6 border-b border-navy-100">
              <h2 className="text-lg font-semibold text-navy-900">{t("saudization.addQuota")}</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("saudization.category")}</label>
                <input type="text" value={quotaForm.category} onChange={(e) => setQuotaForm({ ...quotaForm, category: e.target.value })} className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm" placeholder="e.g. Engineering, Sales" />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("saudization.targetPct")}</label>
                <input type="number" min="0" max="100" value={quotaForm.target_percentage} onChange={(e) => setQuotaForm({ ...quotaForm, target_percentage: e.target.value })} className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm" placeholder="e.g. 30" />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("saudization.notes")}</label>
                <textarea value={quotaForm.notes} onChange={(e) => setQuotaForm({ ...quotaForm, notes: e.target.value })} rows={2} className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm" />
              </div>
            </div>
            <div className="p-6 border-t border-navy-100 flex gap-3 justify-end">
              <button onClick={() => setShowQuotaModal(false)} className="px-4 py-2 text-sm text-navy-600">{t("common.cancel")}</button>
              <button onClick={handleCreateQuota} disabled={!quotaForm.category || !quotaForm.target_percentage} className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium">
                {t("common.save")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
