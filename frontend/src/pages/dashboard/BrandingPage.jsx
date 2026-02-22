import { useState, useEffect, useRef } from "react";
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
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const validTypes = ["image/png", "image/jpeg", "image/svg+xml"];
    if (!validTypes.includes(file.type)) {
      setMessage(t("branding.logoHint"));
      setTimeout(() => setMessage(""), 3000);
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setMessage(t("branding.logoHint"));
      setTimeout(() => setMessage(""), 3000);
      return;
    }
    setUploadingLogo(true);
    try {
      const { data } = await brandingApi.uploadLogo(file);
      setSettings(s => ({ ...s, logo_url: data.logo_url }));
      setMessage(t("branding.logoUploaded"));
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(e.response?.data?.error || "Failed to upload logo");
      setTimeout(() => setMessage(""), 3000);
    } finally {
      setUploadingLogo(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleRemoveLogo = async () => {
    try {
      await brandingApi.removeLogo();
      setSettings(s => ({ ...s, logo_url: "" }));
      setMessage(t("branding.logoRemoved"));
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(e.response?.data?.error || "Failed to remove logo");
      setTimeout(() => setMessage(""), 3000);
    }
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

          {/* Logo Upload */}
          <div>
            <label className="block text-sm font-medium text-navy-700 mb-2">{t("branding.logo")}</label>
            <div className="flex items-center gap-4">
              {settings.logo_url ? (
                <div className="relative">
                  <img src={settings.logo_url} alt="Company logo" className="w-16 h-16 object-contain rounded-lg border border-navy-200 bg-navy-50 p-1" />
                </div>
              ) : (
                <div className="w-16 h-16 rounded-lg border-2 border-dashed border-navy-300 flex items-center justify-center bg-navy-50">
                  <svg className="w-6 h-6 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
              <div className="flex flex-col gap-2">
                <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/svg+xml" onChange={handleLogoUpload} className="hidden" />
                <button onClick={() => fileInputRef.current?.click()} disabled={uploadingLogo}
                  className="text-sm font-medium text-primary-600 hover:text-primary-700 disabled:opacity-50">
                  {uploadingLogo ? t("common.loading") : t("branding.logoUpload")}
                </button>
                {settings.logo_url && (
                  <button onClick={handleRemoveLogo}
                    className="text-sm font-medium text-red-500 hover:text-red-600">
                    {t("branding.removeLogo")}
                  </button>
                )}
                <p className="text-xs text-navy-400">{t("branding.logoHint")}</p>
              </div>
            </div>
          </div>

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
              {settings.logo_url && (
                <img src={settings.logo_url} alt="Logo" className="w-10 h-10 object-contain mx-auto mb-2 rounded" />
              )}
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
