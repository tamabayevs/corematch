import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, "")}/api`
  : "/api";

export default function StatusPage() {
  const { referenceId: urlRefId } = useParams();
  const [referenceId, setReferenceId] = useState(urlRefId || "");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const checkStatus = async (refId) => {
    const id = refId || referenceId;
    if (!id.trim()) return;
    setLoading(true);
    setError("");
    setStatus(null);
    try {
      const res = await fetch(`${API_BASE}/public/candidate-status/${encodeURIComponent(id.trim())}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Not found");
      setStatus(data);
    } catch (e) {
      setError(e.message || "Failed to check status");
    } finally { setLoading(false); }
  };

  // Auto-check if URL has reference ID
  useEffect(() => {
    if (urlRefId) checkStatus(urlRefId);
  }, [urlRefId]);

  const statusSteps = [
    { key: "submitted", label: "Interview Submitted" },
    { key: "under_review", label: "Under Review" },
    { key: "decision_made", label: "Decision Made" },
  ];

  const getStepIndex = (s) => {
    if (!s) return -1;
    return statusSteps.findIndex(step => step.key === s.status);
  };

  const currentStep = status ? getStepIndex(status) : -1;

  return (
    <div className="min-h-screen bg-gradient-to-b from-navy-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-navy-900">CoreMatch</h1>
          <p className="text-navy-500 mt-1">Check your interview status</p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-navy-200 p-6">
          <div className="flex gap-2 mb-6">
            <input
              type="text"
              value={referenceId}
              onChange={e => setReferenceId(e.target.value)}
              placeholder="Enter reference ID (e.g., CM-2026-123456)"
              className="flex-1 border border-navy-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              onKeyDown={e => e.key === "Enter" && checkStatus()}
            />
            <button onClick={() => checkStatus()} disabled={loading}
              className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap">
              {loading ? "..." : "Check"}
            </button>
          </div>

          {error && <div className="text-red-600 text-sm mb-4 bg-red-50 px-3 py-2 rounded-lg">{error}</div>}

          {status && (
            <div className="space-y-4">
              <div className="text-center">
                <p className="text-xs text-navy-400 uppercase tracking-wider">Reference ID</p>
                <p className="text-lg font-bold text-navy-900">{status.reference_id}</p>
              </div>

              <div className="space-y-3 mt-6">
                {statusSteps.map((step, i) => (
                  <div key={step.key} className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      i <= currentStep
                        ? "bg-primary-600 text-white"
                        : "bg-navy-100 text-navy-400"
                    }`}>
                      {i <= currentStep ? "\u2713" : i + 1}
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${i <= currentStep ? "text-navy-900" : "text-navy-400"}`}>
                        {step.label}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {status.submitted_at && (
                <p className="text-xs text-navy-400 text-center mt-4">
                  Submitted: {new Date(status.submitted_at).toLocaleDateString()}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
