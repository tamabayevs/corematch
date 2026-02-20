import { useState, useRef, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";

export default function CameraTestPage() {
  const { token } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const animFrameRef = useRef(null);

  useEffect(() => {
    let mediaStream = null;

    async function initCamera() {
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
          audio: true,
        });
        setStream(mediaStream);

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }

        // Audio level meter
        const audioCtx = new AudioContext();
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        const source = audioCtx.createMediaStreamSource(mediaStream);
        source.connect(analyser);
        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        function updateLevel() {
          analyser.getByteFrequencyData(dataArray);
          const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
          setAudioLevel(Math.min(100, avg * 1.5));
          animFrameRef.current = requestAnimationFrame(updateLevel);
        }
        updateLevel();
      } catch {
        setError(true);
      }
    }

    initCamera();

    return () => {
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  const handleReady = () => {
    // Stop the test stream — RecordingPage will create its own
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    navigate(`/interview/${token}/record/0`);
  };

  const handleRetry = () => {
    setError(false);
    window.location.reload();
  };

  return (
    <Card>
      <h1 className="text-xl font-bold text-navy-900 mb-2">
        {t("interview.camera.title")}
      </h1>
      <p className="text-sm text-navy-500 mb-6">
        {t("interview.camera.description")}
      </p>

      {error ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="font-semibold text-navy-900 mb-2">
            {t("interview.camera.noCamera")}
          </h3>
          <p className="text-sm text-navy-500 mb-4">
            {t("interview.camera.noCameraDesc")}
          </p>
          <Button onClick={handleRetry}>{t("interview.camera.tryAgain")}</Button>
        </div>
      ) : (
        <>
          <div className="relative rounded-lg overflow-hidden bg-black mb-4">
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full"
              style={{ transform: "scaleX(-1)", maxHeight: 400 }}
            />
          </div>

          {/* Audio level meter */}
          <div className="mb-6">
            <p className="text-sm text-navy-500 mb-1">Audio Level</p>
            <div className="w-full bg-navy-200 rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-100"
                style={{ width: `${audioLevel}%` }}
              />
            </div>
          </div>

          <Button onClick={handleReady} className="w-full" size="lg">
            {t("interview.camera.ready")}
          </Button>
        </>
      )}
    </Card>
  );
}
