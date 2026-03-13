import { useState, useEffect } from "react";
import { useI18n } from "../lib/i18n";

const COOKIE_CONSENT_KEY = "corematch_cookie_consent";

export default function CookieConsent() {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Check if user already made a choice
    const consent = localStorage.getItem(COOKIE_CONSENT_KEY);
    if (!consent) {
      // Small delay so it doesn't flash on page load
      const timer = setTimeout(() => setVisible(true), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem(COOKIE_CONSENT_KEY, "accepted");
    setVisible(false);
  };

  const handleDecline = () => {
    localStorage.setItem(COOKIE_CONSENT_KEY, "declined");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-[9999] p-4 sm:p-6 animate-slide-up">
      <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-2xl border border-navy-200 p-5 sm:p-6">
        <div className="flex flex-col sm:flex-row items-start gap-4">
          {/* Icon */}
          <div className="hidden sm:flex shrink-0 items-center justify-center w-10 h-10 rounded-xl bg-primary-50 text-primary-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-navy-900 mb-1">
              {t("cookie.title")}
            </p>
            <p className="text-xs text-navy-500 leading-relaxed">
              {t("cookie.description")}{" "}
              <a href="/privacy" className="text-primary-600 hover:text-primary-700 underline">
                {t("legal.privacy")}
              </a>
            </p>
          </div>

          {/* Buttons */}
          <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
            <button
              onClick={handleDecline}
              className="flex-1 sm:flex-none text-xs font-medium text-navy-600 px-4 py-2 rounded-lg border border-navy-200 hover:bg-navy-50 transition-all"
            >
              {t("cookie.decline")}
            </button>
            <button
              onClick={handleAccept}
              className="flex-1 sm:flex-none text-xs font-semibold text-white bg-primary-600 px-4 py-2 rounded-lg hover:bg-primary-700 transition-all"
            >
              {t("cookie.accept")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
