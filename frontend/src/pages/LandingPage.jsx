import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";
import LanguageToggle from "../components/ui/LanguageToggle";

const API = import.meta.env.VITE_API_URL || "";

/** Fire-and-forget event tracking */
function trackEvent(eventType, extra = {}) {
  try {
    const params = new URLSearchParams(window.location.search);
    fetch(`${API}/api/demand/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_type: eventType,
        page: window.location.pathname,
        referrer: document.referrer || null,
        utm_source: params.get("utm_source") || null,
        utm_medium: params.get("utm_medium") || null,
        utm_campaign: params.get("utm_campaign") || null,
        ...extra,
      }),
    }).catch(() => {});
  } catch {
    // never fail the UI
  }
}

export default function LandingPage() {
  const { t } = useI18n();

  // Track page view on mount
  useEffect(() => {
    trackEvent("page_view");
  }, []);

  /** Track CTA clicks */
  const handleCtaClick = useCallback(() => {
    trackEvent("cta_click");
  }, []);

  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-white/80 backdrop-blur-md border-b border-navy-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <Link to="/" className="text-xl font-bold text-primary-600">
            {t("brand.name")}
          </Link>
          <div className="flex items-center gap-3">
            <LanguageToggle />
            <Link
              to="/login"
              className="text-sm font-medium text-navy-600 hover:text-navy-900 transition-colors"
            >
              {t("auth.login")}
            </Link>
            <Link
              to="/signup"
              className="text-sm font-semibold bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
            >
              {t("landing.startTrial")}
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary-50/50 to-white" />
        <div className="absolute top-20 end-0 w-96 h-96 bg-primary-200/30 rounded-full blur-3xl" />
        <div className="absolute bottom-0 start-0 w-72 h-72 bg-accent-200/20 rounded-full blur-3xl" />

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 bg-primary-50 border border-primary-200 rounded-full px-4 py-1.5 mb-6">
            <span className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-primary-700">{t("landing.badge")}</span>
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy-900 leading-tight mb-6">
            {t("landing.heroTitle")}
          </h1>
          <p className="text-lg sm:text-xl text-navy-500 max-w-2xl mx-auto mb-8">
            {t("landing.heroSubtitle")}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/signup"
              onClick={handleCtaClick}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-primary-600 text-white font-semibold px-8 py-3.5 rounded-xl hover:bg-primary-700 transition-all shadow-lg shadow-primary-600/25 hover:shadow-xl hover:shadow-primary-600/30"
            >
              {t("landing.startTrial")}
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
            <a
              href="#waitlist"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white text-navy-700 font-semibold px-8 py-3.5 rounded-xl border border-navy-200 hover:border-navy-300 hover:shadow-md transition-all"
            >
              {t("landing.waitlistCta")}
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </a>
          </div>
        </div>
      </section>

      {/* Problem Statement */}
      <section className="py-16 px-4 bg-navy-50">
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-lg sm:text-xl text-navy-600 leading-relaxed">
            {t("landing.problemStatement")}
          </p>
        </div>
      </section>

      {/* Value Props */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-navy-900 mb-3">
              {t("landing.whyTitle")}
            </h2>
            <p className="text-navy-500 text-lg">{t("landing.whySubtitle")}</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Card 1: Arabic & RTL */}
            <ValueCard
              icon={
                <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
              }
              title={t("landing.feature1Title")}
              description={t("landing.feature1Desc")}
              color="primary"
            />
            {/* Card 2: AI Scoring */}
            <ValueCard
              icon={
                <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              }
              title={t("landing.feature2Title")}
              description={t("landing.feature2Desc")}
              color="accent"
            />
            {/* Card 3: PDPL & Saudization */}
            <ValueCard
              icon={
                <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              }
              title={t("landing.feature3Title")}
              description={t("landing.feature3Desc")}
              color="primary"
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4 bg-navy-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-navy-900 mb-3">
              {t("landing.howTitle")}
            </h2>
            <p className="text-navy-500 text-lg">{t("landing.howSubtitle")}</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((step) => (
              <div
                key={step}
                className="relative bg-white rounded-2xl p-6 border border-navy-100 shadow-sm"
              >
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary-100 text-primary-600 font-bold text-lg mb-4">
                  {step}
                </div>
                <h3 className="font-semibold text-navy-900 mb-2">
                  {t(`landing.step${step}Title`)}
                </h3>
                <p className="text-sm text-navy-500">
                  {t(`landing.step${step}Desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-4" id="pricing">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-navy-900 mb-3">
              {t("landing.pricingTitle")}
            </h2>
            <p className="text-navy-500 text-lg">{t("landing.pricingSubtitle")}</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Free Trial */}
            <PricingCard
              name={t("landing.planFree")}
              price="$0"
              period={t("landing.planFreePeriod")}
              features={[
                t("landing.planFreeF1"),
                t("landing.planFreeF2"),
                t("landing.planFreeF3"),
                t("landing.planFreeF4"),
              ]}
              ctaLabel={t("landing.startTrial")}
              ctaLink="/signup"
            />
            {/* Starter */}
            <PricingCard
              name={t("landing.planStarter")}
              price="$99"
              period={t("landing.perMonth")}
              features={[
                t("landing.planStarterF1"),
                t("landing.planStarterF2"),
                t("landing.planStarterF3"),
                t("landing.planStarterF4"),
                t("landing.planStarterF5"),
              ]}
              ctaLabel={t("landing.getStarted")}
              ctaLink="/signup"
              featured
            />
            {/* Growth */}
            <PricingCard
              name={t("landing.planGrowth")}
              price="$249"
              period={t("landing.perMonth")}
              features={[
                t("landing.planGrowthF1"),
                t("landing.planGrowthF2"),
                t("landing.planGrowthF3"),
                t("landing.planGrowthF4"),
                t("landing.planGrowthF5"),
              ]}
              ctaLabel={t("landing.getStarted")}
              ctaLink="/signup"
            />
          </div>

          {/* Enterprise callout */}
          <div className="mt-10 text-center">
            <p className="text-navy-500">
              {t("landing.enterpriseCallout")}{" "}
              <a
                href="https://wa.me/966500000000"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 font-semibold hover:text-primary-700"
              >
                {t("landing.contactUs")}
              </a>
            </p>
          </div>
        </div>
      </section>

      {/* Social Proof / Metrics */}
      <section className="py-16 px-4 bg-navy-900">
        <div className="max-w-5xl mx-auto grid sm:grid-cols-3 gap-8 text-center">
          <div>
            <p className="text-3xl font-bold text-white">10x</p>
            <p className="text-primary-300 text-sm mt-1">{t("landing.metric1")}</p>
          </div>
          <div>
            <p className="text-3xl font-bold text-white">95%</p>
            <p className="text-primary-300 text-sm mt-1">{t("landing.metric2")}</p>
          </div>
          <div>
            <p className="text-3xl font-bold text-white">2 min</p>
            <p className="text-primary-300 text-sm mt-1">{t("landing.metric3")}</p>
          </div>
        </div>
      </section>

      {/* Waitlist Form */}
      <section id="waitlist" className="py-20 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl sm:text-4xl font-bold text-navy-900 mb-3">
              {t("landing.waitlistTitle")}
            </h2>
            <p className="text-navy-500 text-lg">{t("landing.waitlistSubtitle")}</p>
          </div>
          <WaitlistForm t={t} />
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-20 px-4 bg-navy-50">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-navy-900 mb-4">
            {t("landing.ctaTitle")}
          </h2>
          <p className="text-lg text-navy-500 mb-8">{t("landing.ctaSubtitle")}</p>
          <Link
            to="/signup"
            onClick={handleCtaClick}
            className="inline-flex items-center gap-2 bg-primary-600 text-white font-semibold px-10 py-4 rounded-xl hover:bg-primary-700 transition-all shadow-lg shadow-primary-600/25 text-lg"
          >
            {t("landing.startTrial")}
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 bg-navy-50 border-t border-navy-100">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <div>
              <p className="text-lg font-bold text-primary-600">{t("brand.name")}</p>
              <p className="text-sm text-navy-400 mt-1">{t("brand.tagline")}</p>
            </div>
            <div className="flex items-center gap-6 text-sm text-navy-500">
              <Link to="/login" className="hover:text-navy-900 transition-colors">
                {t("auth.login")}
              </Link>
              <Link to="/signup" className="hover:text-navy-900 transition-colors">
                {t("auth.signup")}
              </Link>
              <a
                href="https://wa.me/966500000000"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-navy-900 transition-colors"
              >
                {t("landing.contactWhatsApp")}
              </a>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-navy-200 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-navy-400">
            <p>&copy; {new Date().getFullYear()} CoreMatch. {t("landing.allRights")}</p>
            <div className="flex items-center gap-4">
              <Link to="/terms" className="hover:text-navy-700 transition-colors">
                {t("legal.terms")}
              </Link>
              <Link to="/privacy" className="hover:text-navy-700 transition-colors">
                {t("legal.privacy")}
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────

function ValueCard({ icon, title, description, color }) {
  const bg = color === "accent" ? "bg-accent-50" : "bg-primary-50";
  const iconColor = color === "accent" ? "text-accent-600" : "text-primary-600";

  return (
    <div className="bg-white rounded-2xl p-6 border border-navy-100 shadow-sm hover:shadow-md transition-shadow">
      <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl ${bg} ${iconColor} mb-4`}>
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-navy-900 mb-2">{title}</h3>
      <p className="text-sm text-navy-500 leading-relaxed">{description}</p>
    </div>
  );
}

function WaitlistForm({ t }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [status, setStatus] = useState("idle"); // idle | submitting | success | error | duplicate
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim()) return;
    setStatus("submitting");
    setErrorMsg("");

    try {
      const params = new URLSearchParams(window.location.search);
      const res = await fetch(`${API}/api/demand/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          company_name: companyName.trim() || undefined,
          utm_source: params.get("utm_source") || undefined,
          utm_medium: params.get("utm_medium") || undefined,
          utm_campaign: params.get("utm_campaign") || undefined,
        }),
      });

      if (res.ok) {
        setStatus("success");
        trackEvent("waitlist_submit");
      } else if (res.status === 409) {
        setStatus("duplicate");
      } else {
        const data = await res.json().catch(() => ({}));
        setErrorMsg(data.error || "");
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <div className="bg-primary-50 border border-primary-200 rounded-2xl p-8 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary-100 text-primary-600 mb-4">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-lg font-semibold text-primary-800">{t("landing.waitlistSuccess")}</p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-2xl p-8 border border-navy-100 shadow-lg space-y-5"
    >
      {/* Full Name */}
      <div>
        <label className="block text-sm font-medium text-navy-700 mb-1.5">
          {t("landing.waitlistNameLabel")} <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder={t("landing.waitlistNamePlaceholder")}
          required
          className="w-full px-4 py-3 rounded-xl border border-navy-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-navy-900 placeholder:text-navy-300"
        />
      </div>

      {/* Email */}
      <div>
        <label className="block text-sm font-medium text-navy-700 mb-1.5">
          {t("landing.waitlistEmailLabel")} <span className="text-red-500">*</span>
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("landing.waitlistEmailPlaceholder")}
          required
          className="w-full px-4 py-3 rounded-xl border border-navy-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-navy-900 placeholder:text-navy-300"
        />
      </div>

      {/* Company (optional) */}
      <div>
        <label className="block text-sm font-medium text-navy-700 mb-1.5">
          {t("landing.waitlistCompanyLabel")}
        </label>
        <input
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder={t("landing.waitlistCompanyPlaceholder")}
          className="w-full px-4 py-3 rounded-xl border border-navy-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-navy-900 placeholder:text-navy-300"
        />
      </div>

      {/* Error messages */}
      {status === "duplicate" && (
        <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2">
          {t("landing.waitlistErrorDuplicate")}
        </p>
      )}
      {status === "error" && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
          {errorMsg || t("landing.waitlistErrorGeneric")}
        </p>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={status === "submitting"}
        className="w-full py-3.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary-600/25"
      >
        {status === "submitting" ? t("landing.waitlistSubmitting") : t("landing.waitlistCta")}
      </button>
    </form>
  );
}

function PricingCard({ name, price, period, features, ctaLabel, ctaLink, featured }) {
  return (
    <div
      className={`rounded-2xl p-8 border ${
        featured
          ? "border-primary-300 bg-primary-50/30 ring-2 ring-primary-200 shadow-lg relative"
          : "border-navy-100 bg-white shadow-sm"
      }`}
    >
      {featured && (
        <div className="absolute -top-3 start-1/2 -translate-x-1/2 bg-primary-600 text-white text-xs font-bold px-4 py-1 rounded-full">
          POPULAR
        </div>
      )}
      <h3 className="text-lg font-semibold text-navy-900 mb-1">{name}</h3>
      <div className="flex items-baseline gap-1 mb-1">
        <span className="text-4xl font-extrabold text-navy-900">{price}</span>
        <span className="text-navy-400 text-sm">/{period}</span>
      </div>
      <ul className="mt-6 space-y-3 mb-8">
        {features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-navy-600">
            <svg className="w-5 h-5 text-primary-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {f}
          </li>
        ))}
      </ul>
      <Link
        to={ctaLink}
        className={`block w-full text-center py-3 rounded-xl font-semibold transition-all ${
          featured
            ? "bg-primary-600 text-white hover:bg-primary-700 shadow-md"
            : "bg-navy-100 text-navy-700 hover:bg-navy-200"
        }`}
      >
        {ctaLabel}
      </Link>
    </div>
  );
}
