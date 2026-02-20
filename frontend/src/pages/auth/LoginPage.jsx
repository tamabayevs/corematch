import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useAuthStore } from "../../store/authStore";
import Card from "../../components/ui/Card";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import LanguageToggle from "../../components/ui/LanguageToggle";

export default function LoginPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
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
          <p className="text-sm text-navy-400 mt-1">{t("brand.tagline")}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <Input
            id="email"
            label={t("auth.email")}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />

          <Input
            id="password"
            label={t("auth.password")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />

          <div className="flex justify-end">
            <Link
              to="/forgot-password"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              {t("auth.forgotPassword")}
            </Link>
          </div>

          <Button type="submit" loading={loading} className="w-full">
            {t("auth.login")}
          </Button>
        </form>

        <p className="text-center text-sm text-navy-400 mt-6">
          {t("auth.noAccount")}{" "}
          <Link to="/signup" className="text-primary-600 hover:text-primary-700 font-semibold">
            {t("auth.signup")}
          </Link>
        </p>
      </Card>
    </div>
  );
}
