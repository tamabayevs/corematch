import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import Card from "../../components/ui/Card";

export default function AlreadySubmittedPage() {
  const { t } = useI18n();
  const { error } = useInterviewStore();
  const data = error?.data || {};

  return (
    <Card className="text-center">
      <div className="w-20 h-20 mx-auto mb-6 bg-blue-100 rounded-full flex items-center justify-center">
        <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        {t("interview.alreadySubmitted.title")}
      </h1>

      <p className="text-gray-600 mb-4">
        {t("interview.alreadySubmitted.description")}
      </p>

      {data.reference_id && (
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <p className="text-sm font-medium text-gray-900 force-ltr">
            {t("interview.alreadySubmitted.referenceId", { id: data.reference_id })}
          </p>
        </div>
      )}

      {data.job_title && (
        <p className="text-sm text-gray-500 mb-2">
          {data.job_title} — {data.company_name}
        </p>
      )}

      <p className="text-sm text-gray-400 mt-4">
        {t("interview.alreadySubmitted.noResubmit")}
      </p>
    </Card>
  );
}
