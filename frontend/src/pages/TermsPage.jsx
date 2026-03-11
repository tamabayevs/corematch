import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";

export default function TermsPage() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-navy-200">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="text-lg font-bold text-navy-900">CoreMatch</span>
          </Link>
          <Link to="/" className="text-sm text-primary-600 hover:text-primary-700">
            {t("common.back")}
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-navy-900 mb-2">{t("legal.termsTitle")}</h1>
        <p className="text-sm text-navy-500 mb-8">{t("legal.lastUpdated")}: March 11, 2026</p>

        <div className="prose prose-navy max-w-none space-y-6 text-sm text-navy-700 leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">1. {t("legal.acceptance")}</h2>
            <p>{t("legal.acceptanceText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">2. {t("legal.serviceDesc")}</h2>
            <p>{t("legal.serviceDescText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">3. {t("legal.userAccounts")}</h2>
            <p>{t("legal.userAccountsText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">4. {t("legal.dataProcessing")}</h2>
            <p>{t("legal.dataProcessingText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">5. {t("legal.videoContent")}</h2>
            <p>{t("legal.videoContentText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">6. {t("legal.aiScoring")}</h2>
            <p>{t("legal.aiScoringText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">7. {t("legal.payment")}</h2>
            <p>{t("legal.paymentText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">8. {t("legal.termination")}</h2>
            <p>{t("legal.terminationText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">9. {t("legal.liability")}</h2>
            <p>{t("legal.liabilityText")}</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-navy-900 mb-2">10. {t("legal.governing")}</h2>
            <p>{t("legal.governingText")}</p>
          </section>
        </div>

        <div className="mt-12 pt-6 border-t border-navy-200 text-sm text-navy-500">
          <p>{t("legal.contactUs")}: <a href="mailto:legal@corematch.ai" className="text-primary-600">legal@corematch.ai</a></p>
        </div>
      </main>
    </div>
  );
}
