import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { authApi } from "../../api/auth";
import { billingApi } from "../../api/billing";
import Card from "../../components/ui/Card";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Badge from "../../components/ui/Badge";
import Spinner from "../../components/ui/Spinner";

const TIER_LABELS = {
  free: "Free",
  starter: "Starter",
  growth: "Growth",
  enterprise: "Enterprise",
};

const TIER_VARIANTS = {
  free: "default",
  starter: "teal",
  growth: "amber",
  enterprise: "teal",
};

export default function SettingsPage() {
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [billingStatus, setBillingStatus] = useState(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingMessage, setBillingMessage] = useState("");
  const [form, setForm] = useState({
    full_name: "",
    job_title: "",
    company_name: "",
    language: "en",
    notify_on_complete: true,
    notify_weekly: true,
  });

  // Check for billing redirect messages
  useEffect(() => {
    const billing = searchParams.get("billing");
    if (billing === "success") {
      setBillingMessage(t("settings.billingSuccess"));
      // Refresh billing status after successful checkout
      loadBillingStatus();
    } else if (billing === "cancelled") {
      setBillingMessage(t("settings.billingCancelled"));
    }
  }, [searchParams]);

  const loadBillingStatus = async () => {
    try {
      const res = await billingApi.getStatus();
      setBillingStatus(res.data);
    } catch {
      // Billing not available
    }
  };

  useEffect(() => {
    Promise.all([
      authApi.getMe().then((res) => {
        const user = res.data;
        setForm({
          full_name: user.full_name || "",
          job_title: user.job_title || "",
          company_name: user.company_name || "",
          language: user.language || "en",
          notify_on_complete: user.notify_on_complete ?? true,
          notify_weekly: user.notify_weekly ?? true,
        });
      }),
      loadBillingStatus(),
    ]).finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      await authApi.updateMe(form);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch {
      // Handle error
    } finally {
      setSaving(false);
    }
  };

  const handleUpgrade = async (priceId) => {
    setBillingLoading(true);
    try {
      const res = await billingApi.createCheckout(priceId);
      if (res.data.url) {
        window.location.href = res.data.url;
      }
    } catch {
      setBillingMessage(t("settings.billingError"));
    } finally {
      setBillingLoading(false);
    }
  };

  const handleManageBilling = async () => {
    setBillingLoading(true);
    try {
      const res = await billingApi.createPortal();
      if (res.data.url) {
        window.location.href = res.data.url;
      }
    } catch {
      setBillingMessage(t("settings.billingError"));
    } finally {
      setBillingLoading(false);
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
    <div className="space-y-6">
      {success && (
        <div className="bg-primary-50 border border-primary-200 text-primary-700 px-4 py-3 rounded-lg text-sm">
          {t("settings.saved")}
        </div>
      )}

      {billingMessage && (
        <div className="bg-primary-50 border border-primary-200 text-primary-700 px-4 py-3 rounded-lg text-sm">
          {billingMessage}
        </div>
      )}

      {/* Billing & Plan */}
      <Card>
        <h2 className="text-lg font-semibold mb-4">{t("settings.billing")}</h2>
        {billingStatus ? (
          <div className="space-y-4">
            {/* Current Plan */}
            <div className="flex items-center justify-between p-4 bg-navy-50 rounded-lg">
              <div>
                <p className="text-sm text-navy-500">{t("settings.currentPlan")}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-lg font-bold text-navy-900">
                    {TIER_LABELS[billingStatus.plan_tier] || billingStatus.plan_tier}
                  </span>
                  <Badge variant={TIER_VARIANTS[billingStatus.plan_tier] || "default"} dot={false}>
                    {billingStatus.subscription_status === "active" ? t("settings.active") : billingStatus.plan_tier === "free" ? t("settings.freeTier") : (billingStatus.subscription_status || t("settings.freeTier"))}
                  </Badge>
                </div>
              </div>
              {billingStatus.has_stripe ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleManageBilling}
                  loading={billingLoading}
                >
                  {t("settings.manageBilling")}
                </Button>
              ) : null}
            </div>

            {/* Usage */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 border border-navy-200 rounded-lg">
                <p className="text-2xl font-bold text-navy-900">{billingStatus.max_campaigns}</p>
                <p className="text-xs text-navy-500">{t("settings.maxCampaigns")}</p>
              </div>
              <div className="text-center p-3 border border-navy-200 rounded-lg">
                <p className="text-2xl font-bold text-navy-900">
                  {billingStatus.current_candidates_this_month}/{billingStatus.max_candidates_per_month}
                </p>
                <p className="text-xs text-navy-500">{t("settings.candidatesMonth")}</p>
              </div>
              <div className="text-center p-3 border border-navy-200 rounded-lg">
                <p className="text-2xl font-bold text-navy-900">{billingStatus.max_team_members}</p>
                <p className="text-xs text-navy-500">{t("settings.maxTeam")}</p>
              </div>
            </div>

            {/* Upgrade Options */}
            {billingStatus.plan_tier !== "growth" && billingStatus.plan_tier !== "enterprise" && (
              <div className="border-t border-navy-200 pt-4">
                <p className="text-sm font-medium text-navy-700 mb-3">{t("settings.upgradePlan")}</p>
                <div className="flex gap-3">
                  {billingStatus.plan_tier === "free" && (
                    <UpgradeCard
                      name="Starter"
                      price="$99"
                      features={[
                        t("settings.starterF1"),
                        t("settings.starterF2"),
                        t("settings.starterF3"),
                      ]}
                      onUpgrade={() => handleUpgrade(import.meta.env.VITE_STRIPE_STARTER_PRICE_ID)}
                      loading={billingLoading}
                      t={t}
                    />
                  )}
                  <UpgradeCard
                    name="Growth"
                    price="$249"
                    features={[
                      t("settings.growthF1"),
                      t("settings.growthF2"),
                      t("settings.growthF3"),
                    ]}
                    featured
                    onUpgrade={() => handleUpgrade(import.meta.env.VITE_STRIPE_GROWTH_PRICE_ID)}
                    loading={billingLoading}
                    t={t}
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-navy-500">{t("settings.billingNotAvailable")}</p>
        )}
      </Card>

      {/* Profile */}
      <form onSubmit={handleSave} className="space-y-6">
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
            className="rounded-lg border border-navy-200 px-3 py-2 text-sm"
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
                className="h-4 w-4 rounded border-navy-200 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-navy-700">{t("settings.notifyOnComplete")}</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={form.notify_weekly}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, notify_weekly: e.target.checked }))
                }
                className="h-4 w-4 rounded border-navy-200 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-navy-700">{t("settings.notifyWeekly")}</span>
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

function UpgradeCard({ name, price, features, featured, onUpgrade, loading, t }) {
  return (
    <div
      className={`flex-1 p-4 rounded-lg border ${
        featured
          ? "border-primary-300 bg-primary-50/30"
          : "border-navy-200 bg-white"
      }`}
    >
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-lg font-bold text-navy-900">{name}</span>
        <span className="text-sm text-navy-500">{price}/{t("settings.perMonth")}</span>
      </div>
      <ul className="space-y-1 mb-3">
        {features.map((f, i) => (
          <li key={i} className="flex items-center gap-1.5 text-xs text-navy-600">
            <svg className="w-3.5 h-3.5 text-primary-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {f}
          </li>
        ))}
      </ul>
      <Button
        size="sm"
        variant={featured ? "primary" : "secondary"}
        onClick={onUpgrade}
        loading={loading}
        className="w-full"
      >
        {t("settings.upgrade")}
      </Button>
    </div>
  );
}
