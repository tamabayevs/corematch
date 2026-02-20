import { useEffect, useState } from "react";
import { useI18n } from "../../lib/i18n";
import { authApi } from "../../api/auth";
import Card from "../../components/ui/Card";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";

export default function SettingsPage() {
  const { t, locale, setLocale } = useI18n();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    job_title: "",
    company_name: "",
    language: "en",
    notify_on_complete: true,
    notify_weekly: true,
  });

  useEffect(() => {
    authApi
      .getMe()
      .then((res) => {
        const user = res.data;
        setForm({
          full_name: user.full_name || "",
          job_title: user.job_title || "",
          company_name: user.company_name || "",
          language: user.language || "en",
          notify_on_complete: user.notify_on_complete ?? true,
          notify_weekly: user.notify_weekly ?? true,
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      await authApi.updateMe(form);
      setLocale(form.language);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch {
      // Handle error
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t("settings.title")}</h1>

      <form onSubmit={handleSave} className="space-y-6">
        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
            {t("settings.saved")}
          </div>
        )}

        {/* Profile */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">{t("settings.profile")}</h2>
          <div className="space-y-4">
            <Input
              id="full_name"
              label={t("auth.fullName")}
              value={form.full_name}
              onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))}
            />
            <Input
              id="job_title"
              label={t("auth.jobTitle")}
              value={form.job_title}
              onChange={(e) => setForm((prev) => ({ ...prev, job_title: e.target.value }))}
            />
            <Input
              id="company_name"
              label={t("auth.companyName")}
              value={form.company_name}
              onChange={(e) => setForm((prev) => ({ ...prev, company_name: e.target.value }))}
            />
          </div>
        </Card>

        {/* Language */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">{t("settings.languagePref")}</h2>
          <select
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={form.language}
            onChange={(e) => setForm((prev) => ({ ...prev, language: e.target.value }))}
          >
            <option value="en">English</option>
            <option value="ar">العربية</option>
          </select>
        </Card>

        {/* Notifications */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">{t("settings.notifications")}</h2>
          <div className="space-y-3">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={form.notify_on_complete}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, notify_on_complete: e.target.checked }))
                }
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">{t("settings.notifyOnComplete")}</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={form.notify_weekly}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, notify_weekly: e.target.checked }))
                }
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">{t("settings.notifyWeekly")}</span>
            </label>
          </div>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" loading={saving}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </div>
  );
}
