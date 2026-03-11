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
  const { setInviteData, setError, candidate, branding, campaign } = useInterviewStore();
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline = () => setOffline(false);
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

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

  const primaryColor = branding?.primary_color || null;
  const companyName = campaign?.company_name || "CoreMatch";
  const logoUrl = branding?.logo_url || null;

  return (
    <div
      className="min-h-screen bg-navy-50"
      style={primaryColor ? { "--brand-primary": primaryColor } : undefined}
    >
      {/* Offline banner */}
      {offline && (
        <div className="bg-amber-500 text-white text-center py-2 text-sm font-medium">
          {t("offline.banner") || "You are offline. Some features may be unavailable."}
        </div>
      )}

      <header
        className="border-b border-navy-200 px-4 py-3 flex items-center justify-between"
        style={primaryColor
          ? { backgroundColor: primaryColor, borderColor: "transparent" }
          : { backgroundColor: "white" }
        }
      >
        <div className="flex items-center gap-3">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt={companyName}
              className="h-8 w-auto max-w-[120px] object-contain"
            />
          ) : null}
          <h1
            className="text-lg font-bold"
            style={primaryColor ? { color: "white" } : undefined}
          >
            {logoUrl ? "" : (
              <span className={primaryColor ? "text-white" : "text-primary-600"}>
                {companyName}
              </span>
            )}
          </h1>
        </div>
        <LanguageToggle />
      </header>
      <main className="max-w-2xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
