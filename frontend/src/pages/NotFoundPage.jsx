import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";

export default function NotFoundPage() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary-50 text-primary-600 mb-6">
          <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h1 className="text-6xl font-extrabold text-navy-900 mb-2">404</h1>
        <h2 className="text-xl font-semibold text-navy-700 mb-3">
          {t("errors.pageNotFound")}
        </h2>
        <p className="text-navy-500 mb-8">
          {t("errors.pageNotFoundDesc")}
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-primary-600 text-white font-semibold px-6 py-2.5 rounded-xl hover:bg-primary-700 transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            {t("errors.goHome")}
          </Link>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 text-navy-600 font-medium px-6 py-2.5 rounded-xl border border-navy-200 hover:bg-navy-50 transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
            </svg>
            {t("errors.goBack")}
          </button>
        </div>
      </div>
    </div>
  );
}
