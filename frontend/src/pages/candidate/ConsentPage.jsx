import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import { publicApiClient } from "../../api/public";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";

export default function ConsentPage() {
  const { token } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const { candidate } = useInterviewStore();
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);

  // Skip if consent already given
  if (candidate?.consent_given) {
    navigate(`/interview/${token}/camera`, { replace: true });
    return null;
  }

  const handleContinue = async () => {
    if (!agreed) return;
    setLoading(true);
    try {
      await publicApiClient.recordConsent(token);
      navigate(`/interview/${token}/camera`);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <h1 className="text-xl font-bold text-gray-900 mb-4">
        {t("interview.consent.title")}
      </h1>

      <div className="bg-gray-50 rounded-lg p-4 mb-6 text-sm text-gray-700 leading-relaxed">
        {t("interview.consent.text")}
      </div>

      <label className="flex items-start gap-3 mb-6 cursor-pointer">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          className="h-5 w-5 mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        <span className="text-sm text-gray-700 font-medium">
          {t("interview.consent.agree")}
        </span>
      </label>

      <Button
        onClick={handleContinue}
        loading={loading}
        disabled={!agreed}
        className="w-full"
      >
        {t("interview.consent.continue")}
      </Button>
    </Card>
  );
}
