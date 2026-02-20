import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { campaignsApi } from "../../api/campaigns";
import Card from "../../components/ui/Card";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import clsx from "clsx";

const STEPS = ["details", "questions", "settings", "review"];

export default function CampaignCreatePage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    name: "",
    job_title: "",
    job_description: "",
    language: "en",
    questions: [
      { text: "", think_time_seconds: 30 },
      { text: "", think_time_seconds: 30 },
      { text: "", think_time_seconds: 30 },
    ],
    invite_expiry_days: 7,
    max_recording_seconds: 120,
    allow_retakes: true,
  });

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const updateQuestion = (index, field, value) => {
    setForm((prev) => {
      const questions = [...prev.questions];
      questions[index] = { ...questions[index], [field]: value };
      return { ...prev, questions };
    });
  };

  const addQuestion = () => {
    if (form.questions.length >= 7) return;
    setForm((prev) => ({
      ...prev,
      questions: [...prev.questions, { text: "", think_time_seconds: 30 }],
    }));
  };

  const removeQuestion = (index) => {
    if (form.questions.length <= 3) return;
    setForm((prev) => ({
      ...prev,
      questions: prev.questions.filter((_, i) => i !== index),
    }));
  };

  const canNext = () => {
    if (step === 0) return form.name.trim() && form.job_title.trim();
    if (step === 1) return form.questions.every((q) => q.text.trim());
    return true;
  };

  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await campaignsApi.create(form);
      navigate(`/dashboard/campaigns/${res.data.campaign.id}`);
    } catch (err) {
      const data = err.response?.data;
      setError(data?.details?.join(". ") || data?.error || "Failed to create campaign");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        {t("campaign.create")}
      </h1>

      {/* Step indicator */}
      <div className="flex gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={clsx(
              "flex-1 h-2 rounded-full",
              i <= step ? "bg-primary-600" : "bg-gray-200"
            )}
          />
        ))}
      </div>
      <p className="text-sm text-gray-500 mb-6">
        {t("campaign.step", { current: step + 1, total: STEPS.length })}
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}

      <Card>
        {/* Step 0: Details */}
        {step === 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t("campaign.details")}</h2>
            <Input
              id="name"
              label={t("campaign.name")}
              value={form.name}
              onChange={updateField("name")}
              required
            />
            <Input
              id="job_title"
              label={t("campaign.jobTitle")}
              value={form.job_title}
              onChange={updateField("job_title")}
              required
            />
            <div>
              <label htmlFor="job_description" className="block text-sm font-medium text-gray-700 mb-1">
                {t("campaign.jobDescription")}
              </label>
              <textarea
                id="job_description"
                rows={4}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                value={form.job_description}
                onChange={updateField("job_description")}
              />
            </div>
            <div>
              <label htmlFor="language" className="block text-sm font-medium text-gray-700 mb-1">
                {t("campaign.language")}
              </label>
              <select
                id="language"
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.language}
                onChange={updateField("language")}
              >
                <option value="en">English</option>
                <option value="ar">Arabic</option>
                <option value="both">Both</option>
              </select>
            </div>
          </div>
        )}

        {/* Step 1: Questions */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t("campaign.questions")}</h2>
            <p className="text-sm text-gray-500">
              {t("campaign.questionCount", { count: form.questions.length })} (3-7)
            </p>

            {form.questions.map((q, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    {t("candidate.videoAnswer", { index: i + 1 })}
                  </span>
                  {form.questions.length > 3 && (
                    <button
                      type="button"
                      onClick={() => removeQuestion(i)}
                      className="text-sm text-red-600 hover:text-red-700"
                    >
                      {t("campaign.removeQuestion")}
                    </button>
                  )}
                </div>
                <textarea
                  rows={2}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={t("campaign.questionPlaceholder")}
                  value={q.text}
                  onChange={(e) => updateQuestion(i, "text", e.target.value)}
                />
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600">
                    {t("campaign.thinkTime")}:
                  </label>
                  <select
                    className="rounded border border-gray-300 px-2 py-1 text-sm"
                    value={q.think_time_seconds}
                    onChange={(e) =>
                      updateQuestion(i, "think_time_seconds", parseInt(e.target.value))
                    }
                  >
                    {[0, 15, 30, 45, 60, 90, 120].map((s) => (
                      <option key={s} value={s}>
                        {s}s
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}

            {form.questions.length < 7 && (
              <Button variant="secondary" size="sm" onClick={addQuestion}>
                {t("campaign.addQuestion")}
              </Button>
            )}
          </div>
        )}

        {/* Step 2: Settings */}
        {step === 2 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold">{t("campaign.settings")}</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("campaign.inviteExpiry")}
              </label>
              <select
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                value={form.invite_expiry_days}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    invite_expiry_days: parseInt(e.target.value),
                  }))
                }
              >
                {[7, 14, 30].map((d) => (
                  <option key={d} value={d}>
                    {d} {t("campaign.days")}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("campaign.maxRecording")}
              </label>
              <select
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                value={form.max_recording_seconds}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    max_recording_seconds: parseInt(e.target.value),
                  }))
                }
              >
                {[60, 120, 180].map((s) => (
                  <option key={s} value={s}>
                    {s} {t("campaign.seconds")}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="allow_retakes"
                checked={form.allow_retakes}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, allow_retakes: e.target.checked }))
                }
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="allow_retakes" className="text-sm text-gray-700">
                {t("campaign.allowRetakes")}
              </label>
            </div>
          </div>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t("campaign.review")}</h2>
            <dl className="divide-y divide-gray-200">
              <div className="py-3 flex justify-between">
                <dt className="text-sm text-gray-500">{t("campaign.name")}</dt>
                <dd className="text-sm font-medium">{form.name}</dd>
              </div>
              <div className="py-3 flex justify-between">
                <dt className="text-sm text-gray-500">{t("campaign.jobTitle")}</dt>
                <dd className="text-sm font-medium">{form.job_title}</dd>
              </div>
              <div className="py-3 flex justify-between">
                <dt className="text-sm text-gray-500">{t("campaign.language")}</dt>
                <dd className="text-sm font-medium">{form.language.toUpperCase()}</dd>
              </div>
              <div className="py-3 flex justify-between">
                <dt className="text-sm text-gray-500">{t("campaign.questions")}</dt>
                <dd className="text-sm font-medium">{form.questions.length}</dd>
              </div>
              <div className="py-3 flex justify-between">
                <dt className="text-sm text-gray-500">{t("campaign.maxRecording")}</dt>
                <dd className="text-sm font-medium">{form.max_recording_seconds}s</dd>
              </div>
              <div className="py-3 flex justify-between">
                <dt className="text-sm text-gray-500">{t("campaign.allowRetakes")}</dt>
                <dd className="text-sm font-medium">
                  {form.allow_retakes ? t("common.yes") : t("common.no")}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </Card>

      {/* Navigation buttons */}
      <div className="flex justify-between mt-6">
        <Button
          variant="secondary"
          onClick={() => (step === 0 ? navigate("/dashboard") : setStep(step - 1))}
        >
          {t("common.back")}
        </Button>

        {step < 3 ? (
          <Button onClick={() => setStep(step + 1)} disabled={!canNext()}>
            {t("common.next")}
          </Button>
        ) : (
          <Button onClick={handleSubmit} loading={loading}>
            {t("campaign.create")}
          </Button>
        )}
      </div>
    </div>
  );
}
