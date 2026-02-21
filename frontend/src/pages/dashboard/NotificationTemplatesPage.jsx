import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import notificationTemplatesAPI from "../../api/notificationTemplates";

export default function NotificationTemplatesPage() {
  const { t } = useI18n();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [preview, setPreview] = useState(null);
  const [filterType, setFilterType] = useState("");
  const [form, setForm] = useState({ name: "", type: "email", subject: "", body: "", variables: [] });

  useEffect(() => {
    fetchTemplates();
  }, [filterType]);

  const fetchTemplates = async () => {
    try {
      const res = await notificationTemplatesAPI.list(filterType || undefined);
      setTemplates(res.data.templates || []);
    } catch {} finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      // Extract variables from body using {{variable}} pattern
      const vars = [...new Set((form.body + (form.subject || "")).match(/\{\{(\w+)\}\}/g)?.map(v => v.replace(/[{}]/g, "")) || [])];
      const payload = { ...form, variables: vars };
      if (editing) {
        await notificationTemplatesAPI.update(editing, payload);
      } else {
        await notificationTemplatesAPI.create(payload);
      }
      setShowModal(false);
      setEditing(null);
      setForm({ name: "", type: "email", subject: "", body: "", variables: [] });
      fetchTemplates();
    } catch {}
  };

  const handleEdit = (tmpl) => {
    setForm({ name: tmpl.name, type: tmpl.type, subject: tmpl.subject || "", body: tmpl.body, variables: tmpl.variables || [] });
    setEditing(tmpl.id);
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!confirm(t("notifTemplates.deleteConfirm"))) return;
    try {
      await notificationTemplatesAPI.delete(id);
      fetchTemplates();
    } catch {}
  };

  const handlePreview = async (id) => {
    try {
      const res = await notificationTemplatesAPI.preview(id, {});
      setPreview(res.data);
    } catch {}
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("notifTemplates.title")}</h1>
          <p className="text-navy-500 mt-1">{t("notifTemplates.subtitle")}</p>
        </div>
        <button
          onClick={() => { setEditing(null); setForm({ name: "", type: "email", subject: "", body: "", variables: [] }); setShowModal(true); }}
          className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {t("notifTemplates.create")}
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {["", "email", "whatsapp"].map((type) => (
          <button
            key={type}
            onClick={() => setFilterType(type)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filterType === type ? "bg-primary-600 text-white" : "bg-white text-navy-600 border border-navy-200 hover:bg-navy-50"
            }`}
          >
            {type === "" ? t("common.all") : type === "email" ? "Email" : "WhatsApp"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-navy-400">{t("common.loading")}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {templates.map((tmpl) => (
            <div key={tmpl.id} className="bg-white rounded-xl border border-navy-200 p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-navy-900">{tmpl.name}</h3>
                    {tmpl.is_system && (
                      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 bg-navy-100 text-navy-500 rounded font-semibold">
                        System
                      </span>
                    )}
                  </div>
                  <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                    tmpl.type === "email" ? "bg-blue-100 text-blue-700" : tmpl.type === "whatsapp" ? "bg-green-100 text-green-700" : "bg-purple-100 text-purple-700"
                  }`}>
                    {tmpl.type}
                  </span>
                </div>
              </div>

              {tmpl.subject && (
                <p className="text-sm text-navy-600 mt-3 font-medium">{tmpl.subject}</p>
              )}
              <p className="text-sm text-navy-500 mt-2 line-clamp-3">{tmpl.body}</p>

              {tmpl.variables && tmpl.variables.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {tmpl.variables.map((v) => (
                    <span key={v} className="text-[10px] bg-accent-100 text-accent-700 px-1.5 py-0.5 rounded font-mono">
                      {`{{${v}}}`}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex gap-2 mt-4 pt-3 border-t border-navy-100">
                <button onClick={() => handlePreview(tmpl.id)} className="text-xs text-primary-600 hover:text-primary-700 font-medium">
                  {t("notifTemplates.preview")}
                </button>
                {!tmpl.is_system && (
                  <>
                    <button onClick={() => handleEdit(tmpl)} className="text-xs text-navy-500 hover:text-navy-700 font-medium">
                      {t("notifTemplates.edit")}
                    </button>
                    <button onClick={() => handleDelete(tmpl.id)} className="text-xs text-red-500 hover:text-red-700 font-medium">
                      {t("common.delete")}
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
          {templates.length === 0 && (
            <div className="col-span-2 text-center py-12 text-navy-400">
              {t("notifTemplates.noTemplates")}
            </div>
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-navy-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
            <div className="p-6 border-b border-navy-100">
              <h2 className="text-lg font-semibold text-navy-900">
                {editing ? t("notifTemplates.edit") : t("notifTemplates.create")}
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("notifTemplates.name")}</label>
                <input
                  type="text" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("notifTemplates.type")}</label>
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm"
                >
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="both">Both</option>
                </select>
              </div>
              {form.type !== "whatsapp" && (
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">{t("notifTemplates.subject")}</label>
                  <input
                    type="text" value={form.subject}
                    onChange={(e) => setForm({ ...form, subject: e.target.value })}
                    className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm"
                    placeholder="Use {{variable}} for placeholders"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("notifTemplates.body")}</label>
                <textarea
                  value={form.body}
                  onChange={(e) => setForm({ ...form, body: e.target.value })}
                  rows={6}
                  className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm font-mono"
                  placeholder="Hello {{candidate_name}},\n\nYou have been invited..."
                />
              </div>
              <p className="text-xs text-navy-400">
                {t("notifTemplates.variableHint")}
              </p>
            </div>
            <div className="p-6 border-t border-navy-100 flex gap-3 justify-end">
              <button onClick={() => { setShowModal(false); setEditing(null); }} className="px-4 py-2 text-sm text-navy-600 hover:text-navy-800">
                {t("common.cancel")}
              </button>
              <button onClick={handleSave} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
                {t("common.save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {preview && (
        <div className="fixed inset-0 bg-navy-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
            <div className="p-6 border-b border-navy-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-navy-900">{preview.name}</h2>
              <button onClick={() => setPreview(null)} className="text-navy-400 hover:text-navy-600 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {preview.subject_preview && (
                <div>
                  <p className="text-xs font-medium text-navy-500 uppercase">{t("notifTemplates.subject")}</p>
                  <p className="text-sm text-navy-900 mt-1">{preview.subject_preview}</p>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-navy-500 uppercase">{t("notifTemplates.body")}</p>
                <pre className="text-sm text-navy-800 mt-1 whitespace-pre-wrap bg-navy-50 p-4 rounded-lg font-sans">{preview.body_preview}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
