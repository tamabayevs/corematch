import { useEffect, useState, useCallback } from "react";
import { useI18n } from "../../lib/i18n";
import { formatDate, formatDateTime } from "../../lib/formatDate";
import api from "../../api/client";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import clsx from "clsx";

const ACTION_OPTIONS = [
  "",
  "candidate.invited",
  "candidate.shortlisted",
  "candidate.rejected",
  "candidate.hold",
  "candidate.erased",
  "candidate.submitted",
  "campaign.created",
  "retention_policy.updated",
];

const ENTITY_TYPE_OPTIONS = ["", "candidate", "campaign", "user"];

const RETENTION_OPTIONS = [6, 12, 24];

export default function CompliancePage() {
  const { t, locale } = useI18n();

  // Overview state
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);

  // Retention report state
  const [retentionReport, setRetentionReport] = useState([]);
  const [retentionLoading, setRetentionLoading] = useState(true);

  // Retention policy state
  const [retentionMonths, setRetentionMonths] = useState(12);
  const [savingRetention, setSavingRetention] = useState(false);
  const [retentionSaved, setRetentionSaved] = useState(false);

  // Audit log state
  const [auditEntries, setAuditEntries] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotalPages, setAuditTotalPages] = useState(1);
  const [auditLoading, setAuditLoading] = useState(true);

  // Audit log filters
  const [filterAction, setFilterAction] = useState("");
  const [filterEntityType, setFilterEntityType] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");

  // ── Load overview ──
  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const res = await api.get("/compliance/overview");
      setOverview(res.data);
      setRetentionMonths(res.data.retention_months || 12);
    } catch {
      // silent
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  // ── Load retention report ──
  const loadRetentionReport = useCallback(async () => {
    setRetentionLoading(true);
    try {
      const res = await api.get("/compliance/retention-report");
      setRetentionReport(res.data.candidates || []);
    } catch {
      // silent
    } finally {
      setRetentionLoading(false);
    }
  }, []);

  // ── Load audit log ──
  const loadAuditLog = useCallback(async () => {
    setAuditLoading(true);
    try {
      const params = { page: auditPage, per_page: 20 };
      if (filterAction) params.action = filterAction;
      if (filterEntityType) params.entity_type = filterEntityType;
      if (filterFrom) params.from = filterFrom;
      if (filterTo) params.to = filterTo;

      const res = await api.get("/compliance/audit-log", { params });
      setAuditEntries(res.data.entries || []);
      setAuditTotal(res.data.total || 0);
      setAuditTotalPages(res.data.total_pages || 1);
    } catch {
      // silent
    } finally {
      setAuditLoading(false);
    }
  }, [auditPage, filterAction, filterEntityType, filterFrom, filterTo]);

  useEffect(() => {
    loadOverview();
    loadRetentionReport();
  }, [loadOverview, loadRetentionReport]);

  useEffect(() => {
    loadAuditLog();
  }, [loadAuditLog]);

  // ── Save retention policy ──
  const saveRetentionPolicy = async () => {
    setSavingRetention(true);
    setRetentionSaved(false);
    try {
      await api.put("/compliance/retention-policy", {
        retention_months: retentionMonths,
      });
      setRetentionSaved(true);
      loadOverview();
      loadRetentionReport();
      setTimeout(() => setRetentionSaved(false), 3000);
    } catch {
      // silent
    } finally {
      setSavingRetention(false);
    }
  };

  // ── Export CSV ──
  const exportCSV = async () => {
    try {
      const params = {};
      if (filterAction) params.action = filterAction;
      if (filterEntityType) params.entity_type = filterEntityType;
      if (filterFrom) params.from = filterFrom;
      if (filterTo) params.to = filterTo;

      const res = await api.get("/compliance/audit-log/export", {
        params,
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `audit_log_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // silent
    }
  };

  // ── Action badge helper ──
  const actionBadge = (action) => {
    if (!action) return null;
    if (action.includes("erased") || action.includes("rejected") || action.includes("delete")) {
      return <Badge variant="red">{action}</Badge>;
    }
    if (action.includes("hold")) {
      return <Badge variant="amber">{action}</Badge>;
    }
    return <Badge variant="teal">{action}</Badge>;
  };

  // ── Expiry color helper ──
  const expiryClass = (days) => {
    if (days < 0) return "text-red-700 bg-red-50";
    if (days < 7) return "text-red-600 bg-red-50";
    if (days < 30) return "text-amber-600 bg-amber-50";
    return "text-navy-600";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-navy-900">{t("compliance.title")}</h1>
        <p className="text-sm text-navy-500 mt-0.5">{t("compliance.subtitle")}</p>
      </div>

      {/* Overview Cards */}
      {overviewLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : overview ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <OverviewCard
            label={t("compliance.totalCandidates")}
            value={overview.total_candidates}
            color="primary"
          />
          <OverviewCard
            label={t("compliance.erased")}
            value={overview.erased_candidates}
            color="gray"
          />
          <OverviewCard
            label={t("compliance.consentRate")}
            value={`${overview.consent_rate}%`}
            color={overview.consent_rate >= 80 ? "primary" : "accent"}
          />
          <OverviewCard
            label={t("compliance.pendingErasure")}
            value={overview.pending_erasure}
            color={overview.pending_erasure > 0 ? "accent" : "primary"}
          />
        </div>
      ) : null}

      {/* Retention Configuration */}
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-navy-900 mb-1">{t("compliance.retentionPolicy")}</h3>
            <p className="text-sm text-navy-500 max-w-xl">
              {t("compliance.retentionDescription")}
            </p>
          </div>
          {retentionSaved && (
            <Badge variant="teal">{t("settings.saved")}</Badge>
          )}
        </div>
        <div className="flex items-center gap-3 mt-4">
          <select
            value={retentionMonths}
            onChange={(e) => setRetentionMonths(Number(e.target.value))}
            className="rounded-lg border border-navy-200 bg-white px-3 py-2 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {RETENTION_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m} {t("compliance.retentionMonths")}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            onClick={saveRetentionPolicy}
            loading={savingRetention}
          >
            {t("common.save")}
          </Button>
        </div>
      </Card>

      {/* Data Retention Timeline */}
      <Card>
        <h3 className="font-semibold text-navy-900 mb-4">{t("compliance.retentionTimeline")}</h3>
        {retentionLoading ? (
          <div className="flex justify-center py-6">
            <Spinner size="sm" />
          </div>
        ) : retentionReport.length === 0 ? (
          <p className="text-sm text-navy-400 py-4">{t("compliance.noExpiringData")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-100">
                  <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.name")}</th>
                  <th className="text-start py-2 px-3 font-medium text-navy-500">{t("auth.email")}</th>
                  <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.campaignName")}</th>
                  <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.createdAt")}</th>
                  <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.daysUntilExpiry")}</th>
                </tr>
              </thead>
              <tbody>
                {retentionReport.map((cand) => (
                  <tr key={cand.candidate_id} className="border-b border-navy-50 hover:bg-navy-50/50">
                    <td className="py-2.5 px-3 text-navy-700">{cand.full_name}</td>
                    <td className="py-2.5 px-3 text-navy-500">{cand.email}</td>
                    <td className="py-2.5 px-3 text-navy-500">{cand.campaign_name}</td>
                    <td className="py-2.5 px-3 text-navy-500">
                      {cand.created_at ? formatDate(cand.created_at, locale) : ""}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={clsx("px-2 py-0.5 rounded-md text-xs font-semibold", expiryClass(cand.days_until_expiry))}>
                        {cand.days_until_expiry <= 0
                          ? t("compliance.expired")
                          : `${cand.days_until_expiry} ${t("campaign.days")}`}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Audit Log */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-navy-900">{t("compliance.auditLog")}</h3>
          <Button variant="secondary" size="sm" onClick={exportCSV}>
            <svg className="w-4 h-4 me-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {t("compliance.exportCSV")}
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-4">
          <select
            value={filterAction}
            onChange={(e) => { setFilterAction(e.target.value); setAuditPage(1); }}
            className="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">{t("compliance.action")} ({t("common.all")})</option>
            {ACTION_OPTIONS.filter(Boolean).map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>

          <select
            value={filterEntityType}
            onChange={(e) => { setFilterEntityType(e.target.value); setAuditPage(1); }}
            className="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">{t("compliance.entityType")} ({t("common.all")})</option>
            {ENTITY_TYPE_OPTIONS.filter(Boolean).map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>

          <input
            type="date"
            value={filterFrom}
            onChange={(e) => { setFilterFrom(e.target.value); setAuditPage(1); }}
            placeholder={t("insights.dateFrom")}
            className="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <input
            type="date"
            value={filterTo}
            onChange={(e) => { setFilterTo(e.target.value); setAuditPage(1); }}
            placeholder={t("insights.dateTo")}
            className="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />

          {(filterAction || filterEntityType || filterFrom || filterTo) && (
            <button
              onClick={() => {
                setFilterAction("");
                setFilterEntityType("");
                setFilterFrom("");
                setFilterTo("");
                setAuditPage(1);
              }}
              className="text-sm text-navy-500 hover:text-navy-700 underline"
            >
              {t("compliance.clearFilters")}
            </button>
          )}
        </div>

        {/* Audit Table */}
        {auditLoading ? (
          <div className="flex justify-center py-8">
            <Spinner size="sm" />
          </div>
        ) : auditEntries.length === 0 ? (
          <p className="text-sm text-navy-400 py-6 text-center">{t("compliance.noEntries")}</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-navy-100">
                    <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.date")}</th>
                    <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.user")}</th>
                    <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.action")}</th>
                    <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.entityType")}</th>
                    <th className="text-start py-2 px-3 font-medium text-navy-500">{t("compliance.ipAddress")}</th>
                  </tr>
                </thead>
                <tbody>
                  {auditEntries.map((entry) => (
                    <tr key={entry.id} className="border-b border-navy-50 hover:bg-navy-50/50">
                      <td className="py-2.5 px-3 text-navy-500 whitespace-nowrap">
                        {entry.created_at
                          ? formatDateTime(entry.created_at, locale)
                          : ""}
                      </td>
                      <td className="py-2.5 px-3 text-navy-700">
                        {entry.user_name || "System"}
                      </td>
                      <td className="py-2.5 px-3">
                        {actionBadge(entry.action)}
                      </td>
                      <td className="py-2.5 px-3 text-navy-500 capitalize">
                        {entry.entity_type || ""}
                      </td>
                      <td className="py-2.5 px-3 text-navy-400 font-mono text-xs">
                        {entry.ip_address || ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {auditTotalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-navy-100">
                <p className="text-sm text-navy-500">
                  {t("compliance.showing")} {auditEntries.length} {t("compliance.of")} {auditTotal}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={auditPage <= 1}
                    onClick={() => setAuditPage((p) => Math.max(p - 1, 1))}
                  >
                    {t("common.back")}
                  </Button>
                  <span className="flex items-center text-sm text-navy-500 px-2">
                    {auditPage} / {auditTotalPages}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={auditPage >= auditTotalPages}
                    onClick={() => setAuditPage((p) => Math.min(p + 1, auditTotalPages))}
                  >
                    {t("common.next")}
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────

function OverviewCard({ label, value, color }) {
  const dotColor = color === "accent"
    ? "bg-accent-400"
    : color === "gray"
    ? "bg-navy-300"
    : "bg-primary-400";

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
