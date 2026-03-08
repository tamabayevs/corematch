import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../lib/i18n";
import Card from "./ui/Card";
import Button from "./ui/Button";

const STEPS = [
  {
    key: "profile",
    path: "/dashboard/settings",
    icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
  },
  {
    key: "branding",
    path: "/dashboard/branding",
    icon: "M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01",
  },
  {
    key: "campaign",
    path: "/dashboard/campaigns/new",
    icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z",
  },
  {
    key: "invite",
    path: null,
    icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  },
  {
    key: "review",
    path: "/dashboard/reviews",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];

export default function OnboardingChecklist({ campaigns, summary }) {
  const { t } = useI18n();
  const navigate = useNavigate();

  // Derive completion state from actual data
  const completed = {
    profile: true, // They signed up, so profile exists
    branding: !!summary?.branding_set,
    campaign: campaigns.length > 0,
    invite: (summary?.kpis?.candidates_this_month || 0) > 0,
    review: (summary?.kpis?.completion_rate || 0) > 0,
  };

  const completedCount = Object.values(completed).filter(Boolean).length;
  const totalSteps = STEPS.length;
  const progressPct = Math.round((completedCount / totalSteps) * 100);

  // Find the first incomplete step for the CTA
  const nextStep = STEPS.find((s) => !completed[s.key]);

  return (
    <Card className="border-primary-200 bg-gradient-to-br from-white to-primary-50/30">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary-100 mb-3">
          <svg className="w-7 h-7 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-navy-900">{t("onboarding.title")}</h2>
        <p className="text-sm text-navy-500 mt-1">{t("onboarding.subtitle")}</p>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-xs text-navy-500 mb-2">
          <span>{t("onboarding.progress")}</span>
          <span className="font-semibold text-primary-600">{completedCount}/{totalSteps}</span>
        </div>
        <div className="w-full bg-navy-100 rounded-full h-2.5">
          <div
            className="bg-primary-500 h-full rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {STEPS.map((step, idx) => {
          const isDone = completed[step.key];
          const isNext = nextStep?.key === step.key;

          return (
            <button
              key={step.key}
              onClick={() => step.path && navigate(step.path)}
              disabled={!step.path}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-start ${
                isDone
                  ? "bg-primary-50/50 border-primary-200 text-primary-700"
                  : isNext
                  ? "bg-white border-primary-300 text-navy-900 shadow-sm hover:shadow-md"
                  : "bg-white border-navy-150 text-navy-400"
              } ${step.path ? "cursor-pointer hover:border-primary-300" : "cursor-default"}`}
            >
              {/* Checkmark or number */}
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full shrink-0 ${
                  isDone
                    ? "bg-primary-500 text-white"
                    : isNext
                    ? "bg-primary-100 text-primary-600 border-2 border-primary-300"
                    : "bg-navy-100 text-navy-400"
                }`}
              >
                {isDone ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="text-sm font-bold">{idx + 1}</span>
                )}
              </div>

              {/* Icon + text */}
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${isDone ? "line-through" : ""}`}>
                  {t(`onboarding.step.${step.key}`)}
                </p>
                <p className="text-xs text-navy-400 mt-0.5">
                  {t(`onboarding.stepDesc.${step.key}`)}
                </p>
              </div>

              {/* Arrow for clickable items */}
              {step.path && !isDone && (
                <svg className="w-5 h-5 text-navy-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </button>
          );
        })}
      </div>

      {/* CTA */}
      {nextStep?.path && (
        <div className="mt-6 text-center">
          <Button onClick={() => navigate(nextStep.path)} className="px-8">
            {t(`onboarding.cta.${nextStep.key}`)}
          </Button>
        </div>
      )}
    </Card>
  );
}
