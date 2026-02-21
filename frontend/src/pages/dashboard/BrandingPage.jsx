import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { brandingApi } from "../../api/branding";

export default function BrandingPage() {
  const { t } = useI18n();
  const [settings, setSettings] = useState({
    primary_color: "#0D9488",
    secondary_color: "#F59E0B",
    company_website: "",
    logo_url: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await brandingApi.get();
        setSettings(data.branding || settings);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await brandingApi.update(settings);
      setMessage(t("branding.saved"));
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(e.response?.data?.error || "Failed to save");
    } finally { setSaving(false); }
  };

  if (loading) return <div className="text-center py-12 text-navy-500">{t("common.loading")}</div>;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-navy-900">{t("branding.title")}</h1>
        <p className="text-navy-500 mt-1">{t("branding.subtitle")}</p>
      </div>

      {message && (
        <div className="mb-4 bg-primary-50 border border-primary-200 text-primary-700 px-4 py-2 rounded-lg text-sm">{message}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Settings Form */}
        <div className="bg-white border border-navy-200 rounded-xl p-6 space-y-5">
          <h2 className="font-semibold text-navy-900">{t("branding.settings")}</h2>

          <div>
            <label className="block text-sm font-medium text-navy-700 mb-1">{t("branding.primaryColor")}</label>
            <div className="flex items-center gap-3">
              <input type="color" value={settings.primary_color} onChange={e => setSettings(s => ({ ...s, primary_color: e.target.value }))}
                className="w-10 h-10 rounded border border-navy-200 cursor-pointer" />
              <input type="text" value={settings.primary_color} onChange={e => setSettings(s => ({ ...s, primary_color: e.target.value }))}
                className="border border-navy-300 rounded-lg px-3 py-2 text-sm w-28 font-mono" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-navy-700 mb-1">{t("branding.secondaryColor")}</label>
            <div className="flex items-center gap-3">
              <input type="color" value={settings.secondary_color} onChange={e => setSettings(s => ({ ...s, secondary_color: e.target.value }))}
                className="w-10 h-10 rounded border border-navy-200 cursor-pointer" />
              <input type="text" value={settings.secondary_color} onChange={e => setSettings(s => ({ ...s, secondary_color: e.target.value }))}
                className="border border-navy-300 rounded-lg px-3 py-2 text-sm w-28 font-mono" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-navy-700 mb-1">{t("branding.website")}</label>
            <input type="url" value={settings.company_website} onChange={e => setSettings(s => ({ ...s, company_website: e.target.value }))}
              className="w-full border border-navy-300 rounded-lg px-3 py-2 text-sm" placeholder="https://company.com" />
          </div>

          <button onClick={handleSave} disabled={saving}
            className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium">
            {saving ? t("common.loading") : t("common.save")}
          </button>
        </div>

        {/* Preview */}
        <div className="bg-white border border-navy-200 rounded-xl p-6">
          <h2 className="font-semibold text-navy-900 mb-4">{t("branding.preview")}</h2>
          <div className="rounded-xl border border-navy-200 overflow-hidden">
            <div className="p-6 text-center" style={{ backgroundColor: settings.primary_color }}>
              <h3 className="text-xl font-bold text-white">Video Interview</h3>
              <p className="text-white/80 text-sm mt-1">{t("branding.previewWelcome")}</p>
            </div>
            <div className="p-6 space-y-3">
              <div className="h-3 bg-navy-100 rounded-full w-3/4"></div>
              <div className="h-3 bg-navy-100 rounded-full w-1/2"></div>
              <button className="mt-4 px-6 py-2 rounded-lg text-white text-sm font-medium" style={{ backgroundColor: settings.secondary_color }}>
                {t("interview.welcome.begin")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
