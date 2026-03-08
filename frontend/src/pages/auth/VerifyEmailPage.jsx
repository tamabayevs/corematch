import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useAuthStore } from "../../store/authStore";
import { authApi } from "../../api/auth";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import LanguageToggle from "../../components/ui/LanguageToggle";

export default function VerifyEmailPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { user, emailVerified, setEmailVerified, logout } = useAuthStore();
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRefs = useRef([]);

  // If already verified, redirect to dashboard
  useEffect(() => {
    if (emailVerified) {
      navigate("/dashboard", { replace: true });
    }
  }, [emailVerified, navigate]);

  // Countdown timer for resend cooldown
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleChange = (index, value) => {
    // Only allow digits
    const digit = value.replace(/\D/g, "").slice(-1);
    const newCode = [...code];
    newCode[index] = digit;
    setCode(newCode);

    // Auto-focus next input
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) {
      setCode(pasted.split(""));
      inputRefs.current[5]?.focus();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const fullCode = code.join("");
    if (fullCode.length !== 6) {
      setError(t("auth.verifyEmail.invalidCode"));
      return;
    }

    setError("");
    setLoading(true);
    try {
      await authApi.verifyEmail(fullCode);
      setEmailVerified(true);
      setSuccess(t("auth.verifyEmail.success"));
      setTimeout(() => navigate("/dashboard", { replace: true }), 1500);
    } catch (err) {
      setError(err.response?.data?.error || t("auth.verifyEmail.failed"));
      setCode(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResendLoading(true);
    setError("");
    try {
      await authApi.sendVerification();
      setSuccess(t("auth.verifyEmail.codeSent"));
      setResendCooldown(60);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.error || t("auth.verifyEmail.resendFailed"));
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-navy-900 px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-navy-900 via-navy-900 to-primary-950" />
      <div className="absolute top-0 end-0 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 start-0 w-64 h-64 bg-accent-500/5 rounded-full blur-3xl" />

      <div className="absolute top-4 end-4 z-10">
        <LanguageToggle dark />
      </div>

      <Card className="w-full max-w-md relative z-10 border-navy-200 shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary-600">{t("brand.name")}</h1>
          <div className="mt-4">
            <div className="w-16 h-16 mx-auto bg-primary-50 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
          </div>
          <h2 className="text-xl font-semibold text-navy-800 mt-4">{t("auth.verifyEmail.title")}</h2>
          <p className="text-sm text-navy-500 mt-2">
            {t("auth.verifyEmail.subtitle")}{" "}
            <span className="font-medium text-navy-700">{user?.email}</span>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
              {success}
            </div>
          )}

          {/* 6-digit code input */}
          <div className="flex justify-center gap-2" dir="ltr" onPaste={handlePaste}>
            {code.map((digit, i) => (
              <input
                key={i}
                ref={(el) => (inputRefs.current[i] = el)}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                className="w-12 h-14 text-center text-2xl font-bold border-2 border-navy-200 rounded-lg focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none transition-colors"
                autoFocus={i === 0}
              />
            ))}
          </div>

          <Button type="submit" className="w-full" loading={loading} disabled={code.join("").length !== 6}>
            {t("auth.verifyEmail.verify")}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-navy-500">{t("auth.verifyEmail.noCode")}</p>
          <button
            onClick={handleResend}
            disabled={resendLoading || resendCooldown > 0}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resendCooldown > 0
              ? `${t("auth.verifyEmail.resend")} (${resendCooldown}s)`
              : resendLoading
                ? t("auth.verifyEmail.sending")
                : t("auth.verifyEmail.resend")}
          </button>
        </div>

        <div className="mt-4 text-center">
          <button
            onClick={logout}
            className="text-xs text-navy-400 hover:text-navy-600 underline"
          >
            {t("auth.verifyEmail.useAnother")}
          </button>
        </div>
      </Card>
    </div>
  );
}
