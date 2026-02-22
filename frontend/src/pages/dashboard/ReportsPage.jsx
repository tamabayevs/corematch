import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { formatDate } from "../../lib/formatDate";
import reportsAPI from "../../api/reports";

export default function ReportsPage() {
  const { t, locale } = useI18n();
  const [summary, setSummary] = useState(null);
  const [tiers, setTiers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => { fetchData(); }, [dateFrom, dateTo]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (dateFrom) params.from = dateFrom;
      if (dateTo) params.to = dateTo;
      const [sumRes, tierRes] = await Promise.all([
        reportsAPI.executiveSummary(params),
        reportsAPI.tierDistribution(params),
      ]);
      setSummary(sumRes.data);
      setTiers(tierRes.data);
    } catch {} finally { setLoading(false); }
  };

  const handleExportCSV = async () => {
    try {
      const res = await reportsAPI.exportCSV({});
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "corematch-report.csv";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {}
  };

  const handleExportPDF = async () => {
    try {
      const res = await reportsAPI.exportPDF({});
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "corematch-report.pdf";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {}
  };

  const tierColors = {
    strong_proceed: "#0d9488",
    consider: "#f59e0b",
    likely_pass: "#ef4444",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("reports.title")}</h1>
          <p className="text-navy-500 mt-1">{t("reports.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportPDF} className="bg-navy-100 hover:bg-navy-200 text-navy-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            {t("reports.exportPDF")}
          </button>
          <button onClick={handleExportCSV} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            {t("reports.exportCSV")}
          </button>
        </div>
      </div>

      {/* Date filters */}
      <div className="bg-white rounded-xl border border-navy-200 p-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-navy-600">{t("insights.dateFrom")}:</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} lang={locale === "ar" ? "ar" : "en"} className="px-3 py-1.5 border border-navy-300 rounded-lg text-sm" />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-navy-600">{t("insights.dateTo")}:</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} lang={locale === "ar" ? "ar" : "en"} className="px-3 py-1.5 border border-navy-300 rounded-lg text-sm" />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-navy-400">{t("common.loading")}</div>
      ) : summary && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: t("reports.totalCandidates"), value: summary.kpis.total_candidates, color: "text-navy-900" },
              { label: t("reports.completionRate"), value: summary.kpis.completion_rate + "%", color: "text-primary-600" },
              { label: t("reports.shortlistRate"), value: summary.kpis.shortlist_rate + "%", color: "text-green-600" },
              { label: t("reports.avgScore"), value: summary.kpis.avg_score || "—", color: "text-accent-600" },
            ].map((kpi) => (
              <div key={kpi.label} className="bg-white rounded-xl border border-navy-200 p-5">
                <p className="text-sm font-medium text-navy-500">{kpi.label}</p>
                <p className={`text-3xl font-bold mt-1 ${kpi.color}`}>{kpi.value}</p>
              </div>
            ))}
          </div>

          {/* Monthly Trends */}
          {summary.monthly_trends.length > 0 && (
            <div className="bg-white rounded-xl border border-navy-200 p-6">
              <h2 className="text-lg font-semibold text-navy-900 mb-4">{t("reports.monthlyTrends")}</h2>
              <div className="flex items-end gap-2" style={{ height: "200px" }}>
                {summary.monthly_trends.map((m, i) => {
                  const maxVal = Math.max(...summary.monthly_trends.map(t => t.invited)) || 1;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full flex flex-col items-center gap-0.5" style={{ height: "160px", justifyContent: "flex-end" }}>
                        <div className="w-full max-w-[40px] bg-primary-200 rounded-t" style={{ height: `${(m.submitted / maxVal) * 100}%`, minHeight: m.submitted ? "4px" : 0 }} />
                        <div className="w-full max-w-[40px] bg-primary-500 rounded-t -mt-0.5" style={{ height: `${(m.invited / maxVal) * 100}%`, minHeight: m.invited ? "4px" : 0, opacity: 0.3 }} />
                      </div>
                      <span className="text-[10px] text-navy-400">
                        {m.month ? formatDate(m.month, locale, { style: "monthOnly" }) : ""}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-4 mt-4">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded bg-primary-500 opacity-30" />
                  <span className="text-xs text-navy-500">{t("reports.invited")}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded bg-primary-200" />
                  <span className="text-xs text-navy-500">{t("reports.submitted")}</span>
                </div>
              </div>
            </div>
          )}

          {/* Tier Distribution */}
          {tiers && tiers.distribution.length > 0 && (
            <div className="bg-white rounded-xl border border-navy-200 p-6">
              <h2 className="text-lg font-semibold text-navy-900 mb-4">{t("reports.tierDistribution")}</h2>
              <div className="space-y-3">
                {tiers.distribution.map((tier) => (
                  <div key={tier.tier} className="flex items-center gap-4">
                    <span className="w-32 text-sm font-medium text-navy-700 capitalize">{(tier.tier || "").replace("_", " ")}</span>
                    <div className="flex-1 bg-navy-100 rounded-full h-6 overflow-hidden">
                      <div
                        className="h-full rounded-full flex items-center px-2 transition-all"
                        style={{ width: `${Math.max(tier.percentage, 5)}%`, backgroundColor: tierColors[tier.tier] || "#6b7280" }}
                      >
                        <span className="text-[10px] text-white font-bold">{tier.count}</span>
                      </div>
                    </div>
                    <span className="w-16 text-sm text-navy-500 text-end">{tier.percentage}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Campaigns */}
          {summary.top_campaigns.length > 0 && (
            <div className="bg-white rounded-xl border border-navy-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-navy-100">
                <h2 className="text-lg font-semibold text-navy-900">{t("reports.topCampaigns")}</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy-50 text-navy-600">
                    <th className="text-start px-6 py-3 font-medium">{t("reports.campaign")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("reports.candidates")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("reports.submitted")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("reports.avgScore")}</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.top_campaigns.map((c) => (
                    <tr key={c.id} className="border-t border-navy-100">
                      <td className="px-6 py-3">
                        <p className="font-medium text-navy-900">{c.name}</p>
                        <p className="text-xs text-navy-500">{c.job_title}</p>
                      </td>
                      <td className="px-6 py-3 text-navy-600">{c.candidate_count}</td>
                      <td className="px-6 py-3 text-navy-600">{c.submitted_count}</td>
                      <td className="px-6 py-3 text-navy-600">{c.avg_score || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Reviewer Productivity */}
          {summary.reviewer_productivity.length > 0 && (
            <div className="bg-white rounded-xl border border-navy-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-navy-100">
                <h2 className="text-lg font-semibold text-navy-900">{t("reports.reviewerProductivity")}</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy-50 text-navy-600">
                    <th className="text-start px-6 py-3 font-medium">{t("reports.reviewer")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("reports.evaluationsCount")}</th>
                    <th className="text-start px-6 py-3 font-medium">{t("reports.avgRating")}</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.reviewer_productivity.map((r, i) => (
                    <tr key={i} className="border-t border-navy-100">
                      <td className="px-6 py-3 font-medium text-navy-900">{r.name}</td>
                      <td className="px-6 py-3 text-navy-600">{r.evaluations_count}</td>
                      <td className="px-6 py-3 text-navy-600">{r.avg_rating ? r.avg_rating + "/5" : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
