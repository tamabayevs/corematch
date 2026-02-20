import { useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";

export default function WelcomePage() {
  const { token } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const { candidate, campaign, questions } = useInterviewStore();

  if (!campaign) return null;

  const estimatedMinutes = Math.ceil(
    (questions.length * (campaign.max_recording_seconds || 120)) / 60
  );

  return (
    <Card className="text-center">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {t("interview.welcome.title")}
        </h1>
        <p className="text-lg text-gray-700">
          {t("interview.welcome.greeting", { name: candidate?.full_name })}
        </p>
      </div>

      <p className="text-gray-600 mb-6">
        {t("interview.welcome.description", {
          jobTitle: campaign.job_title,
          company: campaign.company_name,
        })}
      </p>

      <div className="flex justify-center gap-6 mb-8 text-sm text-gray-500">
        <span>{t("interview.welcome.questionCount", { count: questions.length })}</span>
        <span>
          {t("interview.welcome.estimatedTime", { minutes: estimatedMinutes })}
        </span>
      </div>

      <Button
        size="lg"
        onClick={() => navigate(`/interview/${token}/consent`)}
        className="mb-8"
      >
        {t("interview.welcome.begin")}
      </Button>

      <div className="bg-blue-50 rounded-lg p-4 text-start">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">
          {t("interview.welcome.tips")}
        </h3>
        <ul className="text-sm text-blue-800 space-y-1.5">
          <li>1. {t("interview.welcome.tip1")}</li>
          <li>2. {t("interview.welcome.tip2")}</li>
          <li>3. {t("interview.welcome.tip3")}</li>
        </ul>
      </div>
    </Card>
  );
}
