import { useLocation } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import Card from "../../components/ui/Card";

export default function ConfirmationPage() {
  const { t } = useI18n();
  const location = useLocation();
  const referenceId = location.state?.referenceId;

  return (
    <Card className="text-center">
      <div className="w-20 h-20 mx-auto mb-6 bg-primary-100 rounded-full flex items-center justify-center">
        <svg className="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h1 className="text-2xl font-bold text-navy-900 mb-2">
        {t("interview.confirmation.title")}
      </h1>

      <p className="text-navy-500 mb-6">
        {t("interview.confirmation.description")}
      </p>

      {referenceId && (
        <div className="bg-navy-50 rounded-lg p-4 mb-6">
          <p className="text-sm text-navy-500 mb-1">
            {t("interview.confirmation.referenceId")}
          </p>
          <p className="text-xl font-bold text-navy-900 force-ltr">{referenceId}</p>
        </div>
      )}

      <div className="bg-primary-50 rounded-lg p-4 text-start">
        <h3 className="text-sm font-semibold text-primary-900 mb-1">
          {t("interview.confirmation.whatNext")}
        </h3>
        <p className="text-sm text-primary-800">
          {t("interview.confirmation.whatNextDesc")}
        </p>
      </div>

      <p className="text-sm text-navy-400 mt-6">
        {t("interview.confirmation.safeToClose")}
      </p>
    </Card>
  );
}
