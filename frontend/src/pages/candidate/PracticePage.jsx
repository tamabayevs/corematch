import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import useMediaRecorder from "../../lib/useMediaRecorder";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";

const STATES = { READY: "ready", RECORDING: "recording", REVIEW: "review" };

export default function PracticePage() {
  const { token } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const { practiceQuestion, campaign } = useInterviewStore();
  const maxDuration = campaign?.max_recording_seconds || 120;

  const [phase, setPhase] = useState(STATES.READY);
  const [elapsed, setElapsed] = useState(0);
  const [previewUrl, setPreviewUrl] = useState(null);
  const videoRef = useRef(null);
  const previewRef = useRef(null);
  const timerRef = useRef(null);

  const onRecordingComplete = useCallback((blob) => {
    const url = URL.createObjectURL(blob);
    setPreviewUrl(url);
    setPhase(STATES.REVIEW);
  }, []);

  const { stream, startRecording, stopRecording } = useMediaRecorder({
    onDataAvailable: onRecordingComplete,
  });

  // Mirror live camera feed
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Recording timer
  useEffect(() => {
    if (phase === STATES.RECORDING) {
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((prev) => {
          if (prev + 1 >= maxDuration) {
            stopRecording();
            clearInterval(timerRef.current);
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [phase, maxDuration, stopRecording]);

  const handleStart = async () => {
    await startRecording();
    setPhase(STATES.RECORDING);
  };

  const handleStop = () => {
    stopRecording();
    clearInterval(timerRef.current);
  };

  const handleRetry = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPhase(STATES.READY);
  };

  const handleContinue = () => {
    // Clean up — practice video is NOT uploaded
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (stream) stream.getTracks().forEach((track) => track.stop());
    navigate(`/interview/${token}/record/0`);
  };

  const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  if (!practiceQuestion) {
    navigate(`/interview/${token}/record/0`, { replace: true });
    return null;
  }

  return (
    <Card>
      {/* Practice badge */}
      <div className="flex items-center gap-2 mb-4">
        <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-2.5 py-1 rounded-full">
          {t("practice.badge") || "PRACTICE"}
        </span>
      </div>

      <h1 className="text-xl font-bold text-navy-900 mb-2">
        {t("practice.title") || "Practice Question"}
      </h1>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-sm text-amber-800">
        {t("practice.disclaimer") || "This is a practice question. Your recording will NOT be saved or scored. Use it to get comfortable with the format."}
      </div>

      <p className="text-navy-700 mb-6 font-medium">
        {practiceQuestion.text || "Tell us about yourself and what makes you a great fit for this role."}
      </p>

      {/* Video area */}
      {phase === STATES.REVIEW && previewUrl ? (
        <div className="relative rounded-lg overflow-hidden bg-black mb-4">
          <video
            ref={previewRef}
            src={previewUrl}
            controls
            className="w-full"
            style={{ maxHeight: 400 }}
          />
        </div>
      ) : (
        <div className="relative rounded-lg overflow-hidden bg-black mb-4">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="w-full"
            style={{ transform: "scaleX(-1)", maxHeight: 400 }}
          />
          {phase === STATES.RECORDING && (
            <div className="absolute top-3 start-3 flex items-center gap-2 bg-red-600 text-white px-3 py-1 rounded-full text-sm font-medium">
              <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
              {formatTime(elapsed)} / {formatTime(maxDuration)}
            </div>
          )}
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-3">
        {phase === STATES.READY && (
          <Button onClick={handleStart} className="flex-1" size="lg">
            {t("practice.startRecording") || "Start Recording"}
          </Button>
        )}

        {phase === STATES.RECORDING && (
          <Button onClick={handleStop} className="flex-1" size="lg" variant="danger">
            {t("practice.stopRecording") || "Stop Recording"}
          </Button>
        )}

        {phase === STATES.REVIEW && (
          <>
            <Button onClick={handleRetry} variant="secondary" className="flex-1">
              {t("practice.tryAgain") || "Try Again"}
            </Button>
            <Button onClick={handleContinue} className="flex-1" size="lg">
              {t("practice.continue") || "Continue to Interview"} →
            </Button>
          </>
        )}
      </div>

      {phase === STATES.READY && (
        <button
          onClick={handleContinue}
          className="mt-4 text-sm text-navy-400 hover:text-navy-600 underline w-full text-center"
        >
          {t("practice.skip") || "Skip practice"}
        </button>
      )}
    </Card>
  );
}
