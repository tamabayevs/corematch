import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { formatDate } from "../../lib/formatDate";
import { dsrApi } from "../../api/dsr";

const STATUS_FILTERS = ["all", "pending", "in_progress", "overdue", "completed"];
const REQUEST_TYPES = ["all", "access", "rectification", "erasure", "portability", "restriction", "objection"];
const DSR_STATUSES = ["pending", "in_progress", "completed", "rejected"];

export default function DSRPage() {
  const { t, locale } = useI18n();

  const [stats, setStats] = useState({ pending: 0, in_progress: 0, overdue: 0, completed: 0 });
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [showNewModal, setShowNewModal] = useState(false);
  const [message, setMessage] = useState("");

  const [form, setForm] = useState({
    subject_name: "",
    subject_email: "",
    request_type: "access",
    description: "",
    deadline: "",
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadRequests();
  }, [statusFilter, typeFilter]);

  const loadData = async () => {
    try {
      await Promise.all([loadStats(), loadRequests()]);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const loadStats = async () => {
    try {
      const { data } = await dsrApi.getStats();
      setStats(data.stats || { pending: 0, in_progress: 0, overdue: 0, completed: 0 });
    } catch (e) { console.error(e); }
  };

  const loadRequests = async () => {
    try {
      const params = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (typeFilter !== "all") params.type = typeFilter;
      const { data } = await dsrApi.list(params);
      setRequests(data.requests || []);
    } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      await dsrApi.create(form);
      setShowNewModal(false);
      setForm({ subject_name: "", subject_email: "", request_type: "access", description: "", deadline: "" });
      setMessage(t("dsr.created"));
      loadData();
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(e.response?.data?.error || "Failed to create request");
    }
  };

  const handleStatusUpdate = async (id, newStatus) => {
    try {
      await dsrApi.update(id, { status: newStatus });
      loadData();
      setMessage(t("dsr.statusUpdated"));
      setTimeout(() => setMessage(""), 3000);
    } catch (e) { console.error(e); }
  };

  const statCards = [
    { key: "pending", label: t("dsr.stats.pending"), color: "bg-accent-50 border-accent-200", textColor: "text-accent-700", dotColor: "bg-accent-400" },
    { key: "in_progress", label: t("dsr.stats.inProgress"), color: "bg-blue-50 border-blue-200", textColor: "text-blue-700", dotColor: "bg-blue-400" },
    { key: "overdue", label: t("dsr.stats.overdue"), color: "bg-red-50 border-red-200", textColor: "text-red-700", dotColor: "bg-red-400" },
    { key: "completed", label: t("dsr.stats.completed"), color: "bg-green-50 border-green-200", textColor: "text-green-700", dotColor: "bg-green-400" },
  ];

  const typeBadge = (type) => {
    const colors = {
      access: "bg-blue-100 text-blue-700",
      rectification: "bg-primary-100 text-primary-700",
      erasure: "bg-red-100 text-red-700",
      portability: "bg-purple-100 text-purple-700",
      restriction: "bg-accent-100 text-accent-700",
      objection: "bg-navy-100 text-navy-600",
    };
    return colors[type] || "bg-navy-100 text-navy-500";
  };

  const statusBadge = (status) => {
    const colors = {
      pending: "bg-accent-100 text-accent-700",
      in_progress: "bg-blue-100 text-blue-700",
      overdue: "bg-red-100 text-red-700",
      completed: "bg-green-100 text-green-700",
      rejected: "bg-navy-100 text-navy-500",
    };
    return colors[status] || "bg-navy-100 text-navy-500";
  };

  if (loading) return <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("dsr.title")}</h1>
          <p className="text-navy-500 mt-1">{t("dsr.subtitle")}</p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {t("dsr.newRequest")}
        </button>
      </div>

      {message && (
        <div className="bg-primary-50 border border-primary-200 text-primary-700 px-4 py-2 rounded-lg text-sm">{message}</div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <button
            key={card.key}
            onClick={() => setStatusFilter(card.key)}
            className={`border rounded-xl p-4 text-start transition-all hover:shadow-sm ${card.color} ${statusFilter === card.key ? "ring-2 ring-primary-400" : ""}`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className={`w-2 h-2 rounded-full ${card.dotColor}`} />
              <span className="text-xs font-medium text-navy-500 uppercase tracking-wide">{card.label}</span>
            </div>
            <p className={`text-2xl font-bold ${card.textColor}`}>{stats[card.key] || 0}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1 bg-navy-100 rounded-lg p-1">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                statusFilter === s ? "bg-white text-navy-900 shadow-sm" : "text-navy-500 hover:text-navy-700"
              }`}
            >
              {s === "all" ? t("common.all") : t(`dsr.statuses.${s}`)}
            </button>
          ))}
        </div>
        <div>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
            className="border border-navy-200 rounded-lg px-3 py-1.5 text-sm bg-white">
            {REQUEST_TYPES.map(type => (
              <option key={type} value={type}>{type === "all" ? t("dsr.allTypes") : t(`dsr.types.${type}`)}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Requests Table */}
      {requests.length === 0 ? (
        <div className="bg-white border border-navy-200 rounded-xl p-12 text-center text-navy-400">
          <svg className="w-12 h-12 mx-auto mb-3 text-navy-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          <p className="text-lg font-medium">{t("dsr.noRequests")}</p>
          <p className="text-sm mt-1">{t("dsr.noRequestsDesc")}</p>
        </div>
      ) : (
        <div className="bg-white border border-navy-200 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-navy-50 border-b border-navy-200">
              <tr>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("dsr.subject")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("auth.email")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("dsr.type")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("candidate.status")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("dsr.deadline")}</th>
                <th className="text-start px-4 py-3 text-xs font-semibold text-navy-500 uppercase">{t("dsr.created")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-100">
              {requests.map((req) => {
                const isOverdue = req.deadline && new Date(req.deadline) < new Date() && req.status !== "completed";
                return (
                  <tr key={req.id} className={`hover:bg-navy-50 ${isOverdue ? "bg-red-50/30" : ""}`}>
                    <td className="px-4 py-3 text-sm font-medium text-navy-900">{req.subject_name}</td>
                    <td className="px-4 py-3 text-sm text-navy-600">{req.subject_email}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeBadge(req.request_type)}`}>
                        {t(`dsr.types.${req.request_type}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge(isOverdue ? "overdue" : req.status)}`}>
                        {isOverdue ? t("dsr.statuses.overdue") : t(`dsr.statuses.${req.status}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-navy-500">
                      {req.deadline ? (
                        <span className={isOverdue ? "text-red-600 font-medium" : ""}>
                          {formatDate(req.deadline, locale)}
                        </span>
                      ) : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-xs text-navy-400">
                      {req.created_at ? formatDate(req.created_at, locale) : "\u2014"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 justify-end">
                        {req.status !== "completed" && (
                          <select
                            value={req.status}
                            onChange={e => handleStatusUpdate(req.id, e.target.value)}
                            className="text-xs border border-navy-200 rounded-lg px-2 py-1 bg-white"
                          >
                            {DSR_STATUSES.map(s => (
                              <option key={s} value={s}>{t(`dsr.statuses.${s}`)}</option>
                            ))}
                          </select>
                        )}
                        {req.status === "completed" && (
                          <span className="text-xs text-green-600 font-medium">{t("dsr.statuses.completed")}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* New Request Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-lg font-bold text-navy-900 mb-4">{t("dsr.newRequest")}</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("dsr.subjectName")}</label>
                  <input type="text" value={form.subject_name}
                    onChange={e => setForm(p => ({ ...p, subject_name: e.target.value }))}
                    className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder={t("dsr.subjectNamePlaceholder")} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("dsr.subjectEmail")}</label>
                  <input type="email" value={form.subject_email}
                    onChange={e => setForm(p => ({ ...p, subject_email: e.target.value }))}
                    className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder={t("dsr.subjectEmailPlaceholder")} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("dsr.requestType")}</label>
                  <select value={form.request_type}
                    onChange={e => setForm(p => ({ ...p, request_type: e.target.value }))}
                    className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm">
                    {REQUEST_TYPES.filter(t => t !== "all").map(type => (
                      <option key={type} value={type}>{t(`dsr.types.${type}`)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("dsr.deadline")}</label>
                  <input type="date" value={form.deadline}
                    onChange={e => setForm(p => ({ ...p, deadline: e.target.value }))}
                    className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("dsr.description")}</label>
                <textarea value={form.description}
                  onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                  rows={3}
                  className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder={t("dsr.descriptionPlaceholder")} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowNewModal(false)} className="px-4 py-2 text-sm text-navy-600 hover:bg-navy-100 rounded-lg">{t("common.cancel")}</button>
              <button onClick={handleCreate}
                disabled={!form.subject_name.trim() || !form.subject_email.trim()}
                className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-40">
                {t("dsr.createRequest")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
