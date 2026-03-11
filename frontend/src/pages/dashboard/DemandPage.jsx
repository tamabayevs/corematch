import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { demandApi } from "../../api/demand";

export default function DemandPage() {
  const { t } = useI18n();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    demandApi
      .stats()
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.error || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-600">
        {error}
      </div>
    );
  }

  const { waitlist, events, linkedin } = data || {};

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-navy-500 mt-1">{t("demand.subtitle")}</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label={t("demand.totalSignups")}
          value={waitlist?.total ?? 0}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          }
          color="primary"
        />
        <KpiCard
          label={t("demand.signupsToday")}
          value={waitlist?.today ?? 0}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          color="accent"
        />
        <KpiCard
          label={t("demand.signupsThisWeek")}
          value={waitlist?.this_week ?? 0}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          }
          color="primary"
        />
        <KpiCard
          label={t("demand.linkedinLeads")}
          value={linkedin?.total_leads ?? 0}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          }
          color="accent"
        />
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Signups Over Time */}
        <ChartCard title={t("demand.signupsOverTime")}>
          {waitlist?.over_time?.length > 0 ? (
            <BarChart data={waitlist.over_time} color="primary" />
          ) : (
            <EmptyChart message={t("demand.noData")} />
          )}
        </ChartCard>

        {/* Page Views Over Time */}
        <ChartCard title={t("demand.pageViewsOverTime")}>
          {events?.page_views_over_time?.length > 0 ? (
            <BarChart data={events.page_views_over_time} color="accent" />
          ) : (
            <EmptyChart message={t("demand.noData")} />
          )}
        </ChartCard>
      </div>

      {/* Breakdowns Row */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Source Breakdown */}
        <BreakdownCard
          title={t("demand.sourceBreakdown")}
          items={waitlist?.source_breakdown?.map((s) => ({ label: s.source, count: s.count })) || []}
        />

        {/* Top Companies */}
        <BreakdownCard
          title={t("demand.topCompanies")}
          items={waitlist?.top_companies?.map((c) => ({ label: c.company, count: c.count })) || []}
        />

        {/* Event Breakdown */}
        <BreakdownCard
          title={t("demand.eventBreakdown")}
          items={events?.breakdown?.map((e) => ({ label: e.event, count: e.count })) || []}
        />
      </div>

      {/* LinkedIn + Referrers Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* LinkedIn Funnel */}
        <ChartCard title={t("demand.linkedinFunnel")}>
          {linkedin?.total_leads > 0 ? (
            <div className="space-y-4">
              <FunnelBar
                label={t("demand.discovered")}
                value={linkedin.funnel?.discovered ?? 0}
                max={linkedin.total_leads}
                color="bg-navy-300"
              />
              <FunnelBar
                label={t("demand.connected")}
                value={linkedin.funnel?.connected ?? 0}
                max={linkedin.total_leads}
                color="bg-primary-500"
              />
              <FunnelBar
                label={t("demand.replied")}
                value={linkedin.funnel?.replied ?? 0}
                max={linkedin.total_leads}
                color="bg-accent-500"
              />
            </div>
          ) : (
            <EmptyChart message={t("demand.noLinkedin")} />
          )}
        </ChartCard>

        {/* Top Referrers */}
        <BreakdownCard
          title={t("demand.topReferrers")}
          items={events?.top_referrers?.map((r) => ({ label: r.referrer, count: r.count })) || []}
        />
      </div>

      {/* Recent Signups Table */}
      <div className="bg-white rounded-xl border border-navy-100 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-navy-100">
          <h3 className="text-lg font-semibold text-navy-900">{t("demand.recentSignups")}</h3>
        </div>
        {waitlist?.recent?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-200 text-start">
                  <th className="px-6 py-3 text-[11px] font-semibold text-navy-400 uppercase tracking-wider text-start">{t("demand.colName")}</th>
                  <th className="px-6 py-3 text-[11px] font-semibold text-navy-400 uppercase tracking-wider text-start">{t("demand.colEmail")}</th>
                  <th className="px-6 py-3 text-[11px] font-semibold text-navy-400 uppercase tracking-wider text-start">{t("demand.colCompany")}</th>
                  <th className="px-6 py-3 text-[11px] font-semibold text-navy-400 uppercase tracking-wider text-start">{t("demand.colSource")}</th>
                  <th className="px-6 py-3 text-[11px] font-semibold text-navy-400 uppercase tracking-wider text-start">{t("demand.colDate")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-100">
                {waitlist.recent.map((row) => (
                  <tr key={row.id} className="hover:bg-navy-50/50 transition-colors">
                    <td className="px-6 py-3 font-medium text-navy-900">{row.full_name}</td>
                    <td className="px-6 py-3 text-navy-600">{row.email}</td>
                    <td className="px-6 py-3 text-navy-500">{row.company_name || "—"}</td>
                    <td className="px-6 py-3">
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700">
                        {row.source}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-navy-500">
                      {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-navy-400">{t("demand.noData")}</div>
        )}
      </div>

      {/* LinkedIn Replied Leads */}
      {linkedin?.replied_leads?.length > 0 && (
        <div className="bg-white rounded-xl border border-navy-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-navy-100">
            <h3 className="text-lg font-semibold text-navy-900">{t("demand.repliedLeads")}</h3>
          </div>
          <div className="divide-y divide-navy-100">
            {linkedin.replied_leads.map((lead, i) => (
              <div key={i} className="px-6 py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-navy-900">{lead.name}</p>
                  <p className="text-sm text-navy-500">
                    {lead.title}{lead.company ? ` · ${lead.company}` : ""}
                  </p>
                </div>
                {lead.linkedin_url && (
                  <a
                    href={lead.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    LinkedIn →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────

function KpiCard({ label, value, icon, color }) {
  const bg = color === "accent" ? "bg-accent-50" : "bg-primary-50";
  const iconColor = color === "accent" ? "text-accent-600" : "text-primary-600";

  return (
    <div className="bg-white rounded-xl border border-navy-100 shadow-sm p-5">
      <div className="flex items-center justify-between mb-3">
        <span className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${bg} ${iconColor}`}>
          {icon}
        </span>
      </div>
      <p className="text-2xl font-bold text-navy-900">{value.toLocaleString()}</p>
      <p className="text-sm text-navy-500 mt-0.5">{label}</p>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-navy-100 shadow-sm p-6">
      <h3 className="text-sm font-semibold text-navy-900 mb-4">{title}</h3>
      {children}
    </div>
  );
}

function EmptyChart({ message }) {
  return (
    <div className="flex items-center justify-center h-40 text-sm text-navy-400">
      {message}
    </div>
  );
}

/** CSS-only bar chart */
function BarChart({ data, color }) {
  const maxVal = Math.max(...data.map((d) => d.count), 1);
  const barColor = color === "accent" ? "bg-accent-500" : "bg-primary-500";

  return (
    <div className="flex items-end gap-1 h-40">
      {data.map((d, i) => {
        const pct = (d.count / maxVal) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center justify-end h-full group relative">
            <div
              className={`w-full rounded-t ${barColor} transition-all min-h-[2px]`}
              style={{ height: `${Math.max(pct, 2)}%` }}
            />
            {/* Tooltip */}
            <div className="absolute -top-8 hidden group-hover:block bg-navy-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
              {d.date}: {d.count}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BreakdownCard({ title, items }) {
  return (
    <div className="bg-white rounded-xl border border-navy-100 shadow-sm p-6">
      <h3 className="text-sm font-semibold text-navy-900 mb-4">{title}</h3>
      {items.length > 0 ? (
        <div className="space-y-3">
          {items.map((item, i) => {
            const maxCount = items[0]?.count || 1;
            const pct = (item.count / maxCount) * 100;
            return (
              <div key={i}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-navy-700 truncate max-w-[70%]">{item.label}</span>
                  <span className="text-navy-900 font-semibold">{item.count}</span>
                </div>
                <div className="h-2 bg-navy-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-sm text-navy-400 text-center py-6">—</div>
      )}
    </div>
  );
}

function FunnelBar({ label, value, max, color }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-navy-700">{label}</span>
        <span className="text-navy-900 font-semibold">{value}</span>
      </div>
      <div className="h-3 bg-navy-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all`}
          style={{ width: `${Math.max(pct, 1)}%` }}
        />
      </div>
    </div>
  );
}
