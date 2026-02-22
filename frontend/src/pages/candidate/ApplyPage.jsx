import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/client";

export default function ApplyPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState(null);
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Form state
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    const loadCampaign = async () => {
      try {
        const { data } = await api.get(`/public/campaign-info/${campaignId}`);
        setCampaign(data.campaign);
        setBranding(data.branding);
      } catch (err) {
        const status = err.response?.status;
        if (status === 404) {
          setError("Campaign not found. Please check the link and try again.");
        } else if (status === 410) {
          setError("This campaign is no longer accepting applications.");
        } else {
          setError("Unable to load campaign information. Please try again later.");
        }
      } finally {
        setLoading(false);
      }
    };
    loadCampaign();
  }, [campaignId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError("");
    setSubmitting(true);

    try {
      const { data } = await api.post(`/public/apply/${campaignId}`, {
        full_name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
      });
      // Redirect to interview welcome page
      navigate(`/interview/${data.invite_token}/welcome`);
    } catch (err) {
      const status = err.response?.status;
      if (status === 409) {
        setSubmitError("You have already applied to this campaign. Check your email for the interview link.");
      } else if (status === 410) {
        setSubmitError("This campaign is no longer accepting applications.");
      } else {
        setSubmitError(err.response?.data?.error || "Failed to submit application. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Unable to Load</h2>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  const primaryColor = branding?.primary_color || "#0D9488";
  const secondaryColor = branding?.secondary_color || "#F59E0B";
  const estimatedMinutes = Math.ceil(
    (campaign.question_count * (campaign.max_recording_seconds || 120)) / 60
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header banner */}
      <div className="py-8 px-4 text-center text-white" style={{ backgroundColor: primaryColor }}>
        <div className="max-w-2xl mx-auto">
          {branding?.logo_url && (
            <img
              src={branding.logo_url}
              alt={campaign.company_name}
              className="w-12 h-12 object-contain mx-auto mb-3 rounded bg-white/20 p-1"
            />
          )}
          <h1 className="text-2xl font-bold mb-1">{campaign.job_title}</h1>
          <p className="text-white/80">{campaign.company_name}</p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 -mt-6">
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          {/* Campaign details */}
          <div className="p-6 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">About this position</h2>
            {campaign.job_description ? (
              <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-line">
                {campaign.job_description}
              </p>
            ) : (
              <p className="text-gray-400 text-sm italic">No description provided.</p>
            )}
            <div className="flex gap-4 mt-4 text-sm text-gray-500">
              <span className="flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {campaign.question_count} questions
              </span>
              <span className="flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                ~{estimatedMinutes} min
              </span>
            </div>
          </div>

          {/* Application form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Apply Now</h2>
            <p className="text-sm text-gray-500">
              Fill in your details below. You will be redirected to the video interview immediately after applying.
            </p>

            {submitError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {submitError}
              </div>
            )}

            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                id="fullName"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                placeholder="Enter your full name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                Phone Number <span className="text-gray-400">(optional)</span>
              </label>
              <input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                placeholder="+966 5X XXX XXXX"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !fullName.trim() || !email.trim()}
              className="w-full py-3 rounded-lg text-white font-medium text-sm disabled:opacity-50 transition-colors"
              style={{ backgroundColor: submitting ? "#9CA3AF" : primaryColor }}
            >
              {submitting ? "Submitting..." : "Start Video Interview"}
            </button>

            <p className="text-xs text-gray-400 text-center mt-2">
              By applying, you consent to recording a video interview for this position.
            </p>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-400 mt-6 mb-8">
          Powered by CoreMatch
        </p>
      </div>
    </div>
  );
}
