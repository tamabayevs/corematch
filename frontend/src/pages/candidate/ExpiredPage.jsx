import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import Card from "../../components/ui/Card";

export default function ExpiredPage() {
  const { t } = useI18n();
  const { error } = useInterviewStore();
  const data = error?.data || {};

  return (
    <Card className="text-center">
      <div className="w-20 h-20 mx-auto mb-6 bg-amber-100 rounded-full flex items-center justify-center">
        <svg className="w-10 h-10 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        {t("interview.expired.title")}
      </h1>

      <p className="text-gray-600 mb-4">
        {t("interview.expired.description")}
      </p>

      {data.job_title && (
        <p className="text-sm text-gray-500 mb-2">
          {data.job_title} — {data.company_name}
        </p>
      )}

      <p className="text-sm text-gray-500 mb-4">
        {t("interview.expired.contact")}
      </p>

      {data.hr_email && (
        <a
          href={`mailto:${data.hr_email}`}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          {t("interview.expired.contactEmail", { email: data.hr_email })}
        </a>
      )}
    </Card>
  );
}
