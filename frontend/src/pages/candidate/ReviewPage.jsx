import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import { publicApiClient } from "../../api/public";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";

export default function ReviewPage() {
  const { token } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const { questions, answers } = useInterviewStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const allRecorded = questions.every((_, i) => answers[i]?.uploaded);

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await publicApiClient.submitInterview(token, !allRecorded);
      // Navigate directly to confirmation — do NOT poll status (409 issue)
      navigate(`/interview/${token}/submit`, {
        state: {
          referenceId: res.data.reference_id,
          uploadedCount: res.data.uploaded_count,
          totalQuestions: res.data.total_questions,
        },
        replace: true,
      });
    } catch (err) {
      const data = err.response?.data;
      if (err.response?.status === 409) {
        // Already submitted
        navigate(`/interview/${token}/submitted`, { replace: true });
      } else {
        setError(data?.error || "Failed to submit interview");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <h1 className="text-xl font-bold text-navy-900 mb-2">
        {t("interview.reviewPage.title")}
      </h1>
      <p className="text-sm text-navy-500 mb-6">
        {t("interview.reviewPage.description")}
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}

      <div className="space-y-3 mb-8">
        {questions.map((q, i) => (
          <div
            key={i}
            className="flex items-center justify-between p-4 border border-navy-200 rounded-lg"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-navy-900 truncate">
                {t("candidate.videoAnswer", { index: i + 1 })}
              </p>
              <p className="text-xs text-navy-500 truncate">{q.text}</p>
            </div>
            <div className="flex items-center gap-3 ms-4">
              {answers[i]?.uploaded ? (
                <Badge variant="teal">{t("interview.reviewPage.recorded")}</Badge>
              ) : (
                <Badge variant="gray">-</Badge>
              )}
              <button
                onClick={() => navigate(`/interview/${token}/record/${i}`)}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium whitespace-nowrap"
              >
                {t("interview.reviewPage.reRecord")}
              </button>
            </div>
          </div>
        ))}
      </div>

      <Button
        onClick={handleSubmit}
        loading={loading}
        className="w-full"
        size="lg"
      >
        {loading ? t("interview.reviewPage.submitting") : t("interview.reviewPage.submitAll")}
      </Button>
    </Card>
  );
}
