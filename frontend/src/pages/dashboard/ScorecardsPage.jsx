import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { scorecardsApi } from "../../api/scorecards";

export default function ScorecardsPage() {
  const { t } = useI18n();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", description: "", competencies: [{ name: "", description: "", weight: 25 }] });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const { data } = await scorecardsApi.listTemplates();
      setTemplates(data.templates || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      if (editing) {
        await scorecardsApi.updateTemplate(editing, form);
      } else {
        await scorecardsApi.createTemplate(form);
      }
      setShowModal(false);
      setEditing(null);
      setForm({ name: "", description: "", competencies: [{ name: "", description: "", weight: 25 }] });
      loadTemplates();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm(t("scorecard.deleteConfirm"))) return;
    try {
      await scorecardsApi.deleteTemplate(id);
      loadTemplates();
    } catch (e) {
      console.error(e);
    }
  };

  const openEdit = (tmpl) => {
    setEditing(tmpl.id);
    setForm({ name: tmpl.name, description: tmpl.description || "", competencies: tmpl.competencies || [] });
    setShowModal(true);
  };

  const addCompetency = () => {
    setForm(prev => ({ ...prev, competencies: [...prev.competencies, { name: "", description: "", weight: 25 }] }));
  };

  const removeCompetency = (idx) => {
    setForm(prev => ({ ...prev, competencies: prev.competencies.filter((_, i) => i !== idx) }));
  };

  const updateCompetency = (idx, field, value) => {
    setForm(prev => ({
      ...prev,
      competencies: prev.competencies.map((c, i) => i === idx ? { ...c, [field]: field === "weight" ? Number(value) : value } : c),
    }));
  };

  if (loading) return <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("scorecard.title")}</h1>
          <p className="text-navy-500 mt-1">{t("scorecard.subtitle")}</p>
        </div>
        <button
          onClick={() => { setEditing(null); setForm({ name: "", description: "", competencies: [{ name: "", description: "", weight: 25 }] }); setShowModal(true); }}
          className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {t("scorecard.create")}
        </button>
      </div>

      {templates.length === 0 ? (
        <div className="text-center py-16 text-navy-400">
          <p className="text-lg font-medium">{t("scorecard.noTemplates")}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {templates.map((tmpl) => (
            <div key={tmpl.id} className="bg-white border border-navy-200 rounded-xl p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-navy-900 truncate">{tmpl.name}</h3>
                    {tmpl.is_system && (
                      <span className="text-[10px] font-semibold uppercase tracking-wider bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full">
                        {t("template.system")}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-navy-500 mt-1 line-clamp-2">{tmpl.description}</p>
                  <p className="text-xs text-navy-400 mt-2">
                    {(tmpl.competencies || []).length} {t("scorecard.competencies")}
                  </p>
                </div>
                {!tmpl.is_system && (
                  <div className="flex gap-1 ms-3">
                    <button onClick={() => openEdit(tmpl)} className="text-navy-400 hover:text-primary-600 p-1.5 rounded-lg hover:bg-navy-100">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                    </button>
                    <button onClick={() => handleDelete(tmpl.id)} className="text-navy-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {(tmpl.competencies || []).map((c, i) => (
                  <span key={i} className="text-xs bg-navy-100 text-navy-600 px-2 py-0.5 rounded-full">
                    {c.name} ({c.weight}%)
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-lg font-bold text-navy-900 mb-4">{editing ? t("scorecard.edit") : t("scorecard.create")}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("scorecard.name")}</label>
                <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                  className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("scorecard.description")}</label>
                <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} rows={2}
                  className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-navy-700">{t("scorecard.competencies")}</label>
                  <button onClick={addCompetency} className="text-xs text-primary-600 hover:text-primary-700 font-medium">+ {t("scorecard.addCompetency")}</button>
                </div>
                <div className="space-y-2">
                  {form.competencies.map((c, i) => (
                    <div key={i} className="flex gap-2 items-start bg-navy-50 rounded-lg p-3">
                      <div className="flex-1 space-y-1">
                        <input type="text" placeholder={t("scorecard.competencyName")} value={c.name}
                          onChange={e => updateCompetency(i, "name", e.target.value)}
                          className="w-full border border-navy-200 rounded px-2 py-1 text-sm" />
                        <input type="text" placeholder={t("scorecard.competencyDesc")} value={c.description || ""}
                          onChange={e => updateCompetency(i, "description", e.target.value)}
                          className="w-full border border-navy-200 rounded px-2 py-1 text-xs text-navy-500" />
                      </div>
                      <div className="flex items-center gap-1">
                        <input type="number" value={c.weight} onChange={e => updateCompetency(i, "weight", e.target.value)}
                          className="w-16 border border-navy-200 rounded px-2 py-1 text-sm text-center" min="1" max="100" />
                        <span className="text-xs text-navy-400">%</span>
                      </div>
                      {form.competencies.length > 1 && (
                        <button onClick={() => removeCompetency(i)} className="text-red-400 hover:text-red-600 p-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => { setShowModal(false); setEditing(null); }} className="px-4 py-2 text-sm text-navy-600 hover:bg-navy-100 rounded-lg">{t("common.cancel")}</button>
              <button onClick={handleSave} className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium">{t("common.save")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
