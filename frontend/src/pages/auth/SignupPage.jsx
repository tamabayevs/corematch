import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useAuthStore } from "../../store/authStore";
import Card from "../../components/ui/Card";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import LanguageToggle from "../../components/ui/LanguageToggle";

export default function SignupPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { signup } = useAuthStore();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirmPassword: "",
    company_name: "",
  });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  const validateForm = () => {
    const newErrors = {};
    if (!form.full_name.trim()) newErrors.full_name = t("common.required");
    if (!form.email.trim()) newErrors.email = t("common.required");
    if (form.password.length < 8)
      newErrors.password = t("auth.passwordRequirements");
    else if (!/[A-Z]/.test(form.password))
      newErrors.password = t("auth.passwordRequirements");
    else if (!/\d/.test(form.password))
      newErrors.password = t("auth.passwordRequirements");
    if (form.password !== form.confirmPassword)
      newErrors.confirmPassword = "Passwords do not match";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError("");
    if (!validateForm()) return;

    setLoading(true);
    try {
      await signup({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        company_name: form.company_name,
      });
      navigate("/dashboard");
    } catch (err) {
      const data = err.response?.data;
      if (data?.details) {
        setServerError(data.details.join(". "));
      } else {
        setServerError(data?.error || "Signup failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
      <div className="absolute top-4 end-4">
        <LanguageToggle />
      </div>

      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary-600">{t("brand.name")}</h1>
          <p className="text-sm text-gray-500 mt-1">{t("auth.signup")}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {serverError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {serverError}
            </div>
          )}

          <Input
            id="full_name"
            label={t("auth.fullName")}
            value={form.full_name}
            onChange={updateField("full_name")}
            error={errors.full_name}
            required
          />

          <Input
            id="email"
            label={t("auth.email")}
            type="email"
            value={form.email}
            onChange={updateField("email")}
            error={errors.email}
            required
            autoComplete="email"
          />

          <Input
            id="company_name"
            label={t("auth.companyName")}
            value={form.company_name}
            onChange={updateField("company_name")}
          />

          <Input
            id="password"
            label={t("auth.password")}
            type="password"
            value={form.password}
            onChange={updateField("password")}
            error={errors.password}
            required
            autoComplete="new-password"
          />
          <p className="text-xs text-gray-500 -mt-2">
            {t("auth.passwordRequirements")}
          </p>

          <Input
            id="confirmPassword"
            label={t("auth.confirmPassword")}
            type="password"
            value={form.confirmPassword}
            onChange={updateField("confirmPassword")}
            error={errors.confirmPassword}
            required
            autoComplete="new-password"
          />

          <Button type="submit" loading={loading} className="w-full">
            {t("auth.signup")}
          </Button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          {t("auth.hasAccount")}{" "}
          <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
            {t("auth.login")}
          </Link>
        </p>
      </Card>
    </div>
  );
}
