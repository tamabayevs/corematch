import { useEffect, useState } from "react";
import { Outlet, useParams, useNavigate } from "react-router-dom";
import { publicApiClient } from "../api/public";
import { useInterviewStore } from "../store/interviewStore";
import { useI18n } from "../lib/i18n";
import LanguageToggle from "./ui/LanguageToggle";
import Spinner from "./ui/Spinner";

export default function InterviewLayout() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { t } = useI18n();
  const { setInviteData, setError, candidate } = useInterviewStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function fetchInvite() {
      try {
        const res = await publicApiClient.getInvite(token);
        if (cancelled) return;
        setInviteData(res.data);
      } catch (err) {
        if (cancelled) return;
        const status = err.response?.status;
        const data = err.response?.data;

        if (status === 410) {
          setError("expired", data);
          navigate(`/interview/${token}/expired`, { replace: true });
        } else if (status === 409) {
          setError("submitted", data);
          navigate(`/interview/${token}/submitted`, { replace: true });
        } else {
          setError("unknown", { message: data?.error || "Failed to load interview" });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchInvite();
    return () => { cancelled = true; };
  }, [token, navigate, setInviteData, setError]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-navy-50">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy-50">
      <header className="bg-white border-b border-navy-200 px-4 py-3 flex items-center justify-between">
        <h1 className="text-lg font-bold text-primary-600">CoreMatch</h1>
        <LanguageToggle />
      </header>
      <main className="max-w-2xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
