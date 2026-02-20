import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useInterviewStore } from "../../store/interviewStore";
import { publicApiClient } from "../../api/public";
import useMediaRecorder from "../../lib/useMediaRecorder";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import clsx from "clsx";

// State machine: PREP → RECORDING → REVIEW → UPLOADING → COMPLETE
const STATES = { PREP: "prep", RECORDING: "recording", REVIEW: "review", UPLOADING: "uploading", COMPLETE: "complete" };

export default function RecordingPage() {
  const { token, qi } = useParams();
  const questionIndex = parseInt(qi);
  const { t } = useI18n();
  const navigate = useNavigate();
  const { questions, campaign, setAnswer } = useInterviewStore();

  const question = questions[questionIndex];
  const totalQuestions = questions.length;
  const thinkTime = question?.think_time_seconds || 0;
  const maxDuration = campaign?.max_recording_seconds || 120;
  const allowRetakes = campaign?.allow_retakes ?? true;

  const [phase, setPhase] = useState(thinkTime > 0 ? STATES.PREP : STATES.RECORDING);
  const [prepCountdown, setPrepCountdown] = useState(thinkTime);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(false);
  const [reviewUrl, setReviewUrl] = useState(null);

  const videoRef = useRef(null);
  const reviewVideoRef = useRef(null);
  const streamRef = useRef(null);

  const {
    elapsed,
    blob,
    startRecording,
    stopRecording,
    reset,
    remaining,
  } = useMediaRecorder({ maxDuration });

  // Initialize camera and start prep/recording
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
          audio: true,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        if (thinkTime <= 0) {
          startRecording(stream);
        }
      } catch {
        // Camera error — handled by camera test page
      }
    }

    init();

    return () => {
      cancelled = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, [questionIndex]);

  // Prep countdown
  useEffect(() => {
    if (phase !== STATES.PREP || prepCountdown <= 0) return;

    const timer = setInterval(() => {
      setPrepCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setPhase(STATES.RECORDING);
          if (streamRef.current) {
            startRecording(streamRef.current);
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [phase, prepCountdown, startRecording]);

  // When blob is available (recording stopped), move to review
  useEffect(() => {
    if (blob && phase === STATES.RECORDING) {
      const url = URL.createObjectURL(blob);
      setReviewUrl(url);
      setPhase(STATES.REVIEW);
    }
  }, [blob, phase]);

  const handleStop = () => {
    stopRecording();
  };

  const handleReRecord = () => {
    if (reviewUrl) URL.revokeObjectURL(reviewUrl);
    setReviewUrl(null);
    reset();
    setUploadError(false);
    setPrepCountdown(thinkTime);
    setPhase(thinkTime > 0 ? STATES.PREP : STATES.RECORDING);

    // Restart recording with existing stream
    if (streamRef.current && thinkTime <= 0) {
      startRecording(streamRef.current);
    }
  };

  const handleUpload = async () => {
    if (!blob) return;
    setPhase(STATES.UPLOADING);
    setUploadProgress(0);
    setUploadError(false);

    const formData = new FormData();
    formData.append("video", blob, `q${questionIndex}.webm`);
    formData.append("question_index", questionIndex);
    formData.append("duration_seconds", elapsed);

    try {
      const res = await publicApiClient.uploadVideo(token, formData, (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
        setUploadProgress(progress);
      });

      setAnswer(questionIndex, {
        blob,
        uploaded: true,
        videoAnswerId: res.data.video_answer_id,
      });

      setPhase(STATES.COMPLETE);

      // Auto-advance after 1s
      setTimeout(() => {
        // Clean up
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
        }
        if (reviewUrl) URL.revokeObjectURL(reviewUrl);

        if (questionIndex + 1 < totalQuestions) {
          navigate(`/interview/${token}/record/${questionIndex + 1}`);
        } else {
          navigate(`/interview/${token}/review`);
        }
      }, 1000);
    } catch {
      setUploadError(true);
      setPhase(STATES.REVIEW);
    }
  };

  if (!question) return null;

  return (
    <Card>
      {/* Question header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-primary-600">
          {t("interview.recording.question", {
            current: questionIndex + 1,
            total: totalQuestions,
          })}
        </p>
        {phase === STATES.RECORDING && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-red-600">
              {t("interview.recording.recording")}
            </span>
          </div>
        )}
      </div>

      <h2 className="text-lg font-semibold text-gray-900 mb-4">{question.text}</h2>

      {/* PREP phase */}
      {phase === STATES.PREP && (
        <div className="text-center py-8">
          <h3 className="text-xl font-bold text-gray-900 mb-2">
            {t("interview.recording.prepTitle")}
          </h3>
          <p className="text-gray-500 mb-6">
            {t("interview.recording.prepDescription")}
          </p>
          <div className="text-5xl font-bold text-primary-600 mb-4">
            {prepCountdown}
          </div>
          <p className="text-sm text-gray-500">
            {t("interview.recording.startIn", { seconds: prepCountdown })}
          </p>
          {/* Camera preview during prep */}
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="w-full mt-6 rounded-lg"
            style={{ transform: "scaleX(-1)", maxHeight: 300 }}
          />
        </div>
      )}

      {/* RECORDING phase */}
      {phase === STATES.RECORDING && (
        <div>
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="w-full rounded-lg bg-black mb-4"
            style={{ transform: "scaleX(-1)", maxHeight: 400 }}
          />

          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-gray-500">
              {formatTime(elapsed)}
            </span>
            <span className="text-sm text-gray-500">
              {t("interview.recording.timeRemaining", { seconds: remaining })}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-red-500 h-2 rounded-full transition-all"
              style={{ width: `${(elapsed / maxDuration) * 100}%` }}
            />
          </div>

          <Button variant="danger" onClick={handleStop} className="w-full">
            {t("interview.recording.stopRecording")}
          </Button>
        </div>
      )}

      {/* REVIEW phase */}
      {phase === STATES.REVIEW && (
        <div>
          <h3 className="font-semibold mb-3">{t("interview.recording.review")}</h3>

          {reviewUrl && (
            <video
              ref={reviewVideoRef}
              controls
              className="w-full rounded-lg bg-black mb-4"
              style={{ maxHeight: 400 }}
              src={reviewUrl}
            />
          )}

          {uploadError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {t("interview.recording.uploadFailed")}
            </div>
          )}

          <div className="flex gap-3">
            {allowRetakes && (
              <Button variant="secondary" onClick={handleReRecord} className="flex-1">
                {t("interview.recording.reRecord")}
              </Button>
            )}
            <Button onClick={handleUpload} className="flex-1">
              {t("interview.recording.useThis")}
            </Button>
          </div>
        </div>
      )}

      {/* UPLOADING phase */}
      {phase === STATES.UPLOADING && (
        <div className="text-center py-8">
          <p className="text-lg font-medium mb-4">{t("interview.recording.uploading")}</p>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm text-gray-500">{uploadProgress}%</p>
        </div>
      )}

      {/* COMPLETE phase */}
      {phase === STATES.COMPLETE && (
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-lg font-medium text-green-700">
            {t("interview.recording.uploadComplete")}
          </p>
        </div>
      )}
    </Card>
  );
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
