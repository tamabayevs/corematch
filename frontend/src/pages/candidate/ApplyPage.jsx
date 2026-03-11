import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../../api/client";

const MAX_CV_SIZE_MB = 10;
const ACCEPTED_CV_TYPES = ".pdf,.docx";

export default function ApplyPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [campaign, setCampaign] = useState(null);
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Form state
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [cvFile, setCvFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [referenceId, setReferenceId] = useState("");

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

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_CV_SIZE_MB * 1024 * 1024) {
      setSubmitError(`File too large. Maximum size is ${MAX_CV_SIZE_MB}MB.`);
      return;
    }
    setSubmitError("");
    setCvFile(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError("");
    setSubmitting(true);

    try {
      const isPipeline = campaign?.pipeline_enabled;

      if (isPipeline) {
        // Pipeline flow: use multipart/form-data for CV upload
        const formData = new FormData();
        formData.append("full_name", fullName.trim());
        formData.append("email", email.trim());
        if (phone.trim()) formData.append("phone", phone.trim());
        if (linkedinUrl.trim()) formData.append("linkedin_url", linkedinUrl.trim());
        if (cvFile) formData.append("cv", cvFile);

        const { data } = await api.post(`/public/apply/${campaignId}`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        // Pipeline: show confirmation page (no immediate interview redirect)
        setReferenceId(data.reference_id);
        setSubmitted(true);
      } else {
        // Standard flow: JSON body, redirect to interview
        const { data } = await api.post(`/public/apply/${campaignId}`, {
          full_name: fullName.trim(),
          email: email.trim(),
          phone: phone.trim() || null,
        });
        navigate(`/interview/${data.invite_token}/welcome`);
      }
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
  const isPipeline = campaign?.pipeline_enabled;
  const estimatedMinutes = Math.ceil(
    (campaign.question_count * (campaign.max_recording_seconds || 120)) / 60
  );

  // Pipeline confirmation screen after submission
  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="py-8 px-4 text-center text-white" style={{ backgroundColor: primaryColor }}>
          <div className="max-w-2xl mx-auto">
            {branding?.logo_url && (
              <img src={branding.logo_url} alt={campaign.company_name}
                className="w-12 h-12 object-contain mx-auto mb-3 rounded bg-white/20 p-1" />
            )}
            <h1 className="text-2xl font-bold mb-1">{campaign.job_title}</h1>
            <p className="text-white/80">{campaign.company_name}</p>
          </div>
        </div>
        <div className="max-w-2xl mx-auto px-4 -mt-6">
          <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Application Received!</h2>
            <p className="text-gray-500 mb-4">
              Your application is being reviewed by our AI screening system. We will contact you
              if you advance to the video interview stage.
            </p>
            {referenceId && (
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-gray-500">Your reference number</p>
                <p className="text-lg font-mono font-bold text-gray-900">{referenceId}</p>
              </div>
            )}
            <p className="text-xs text-gray-400">
              Save your reference number to check your application status.
            </p>
          </div>
          <p className="text-center text-xs text-gray-400 mt-6 mb-8">Powered by CoreMatch</p>
        </div>
      </div>
    );
  }

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
              {isPipeline
                ? "Upload your CV and fill in your details. Our AI will review your profile before inviting you to a video interview."
                : "Fill in your details below. You will be redirected to the video interview immediately after applying."}
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

            {/* Pipeline-only fields */}
            {isPipeline && (
              <>
                <div>
                  <label htmlFor="linkedin" className="block text-sm font-medium text-gray-700 mb-1">
                    LinkedIn Profile <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    id="linkedin"
                    type="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                    placeholder="https://linkedin.com/in/your-profile"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Upload CV <span className="text-gray-400">(PDF or DOCX, max {MAX_CV_SIZE_MB}MB)</span>
                  </label>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-teal-400 hover:bg-teal-50/30 transition-colors"
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={ACCEPTED_CV_TYPES}
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    {cvFile ? (
                      <div className="flex items-center justify-center gap-3">
                        <svg className="w-8 h-8 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <div className="text-start">
                          <p className="text-sm font-medium text-gray-900">{cvFile.name}</p>
                          <p className="text-xs text-gray-500">
                            {(cvFile.size / 1024 / 1024).toFixed(1)} MB
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setCvFile(null);
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                          className="ms-auto text-gray-400 hover:text-red-500"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <>
                        <svg className="w-10 h-10 text-gray-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-sm text-gray-500">
                          Click to upload or drag and drop
                        </p>
                        <p className="text-xs text-gray-400 mt-1">PDF or DOCX</p>
                      </>
                    )}
                  </div>
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={submitting || !fullName.trim() || !email.trim()}
              className="w-full py-3 rounded-lg text-white font-medium text-sm disabled:opacity-50 transition-colors"
              style={{ backgroundColor: submitting ? "#9CA3AF" : primaryColor }}
            >
              {submitting
                ? "Submitting..."
                : isPipeline
                  ? "Submit Application"
                  : "Start Video Interview"}
            </button>

            <p className="text-xs text-gray-400 text-center mt-2">
              {isPipeline
                ? "By applying, you consent to AI-assisted screening of your profile for this position."
                : "By applying, you consent to recording a video interview for this position."}
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
