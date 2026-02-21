import { useState, useRef, useCallback } from "react";

export default function useMediaRecorder({ maxDuration = 120, onStop }) {
  const [state, setState] = useState("idle"); // idle | recording | paused
  const [elapsed, setElapsed] = useState(0);
  const [blob, setBlob] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);
  const streamRef = useRef(null);

  const startRecording = useCallback(
    async (stream) => {
      streamRef.current = stream;
      chunksRef.current = [];
      setBlob(null);
      setElapsed(0);

      const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
        ? "video/webm;codecs=vp9"
        : "video/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const recordedBlob = new Blob(chunksRef.current, { type: mimeType });
        setBlob(recordedBlob);
        setState("idle");
        clearInterval(timerRef.current);
        onStop?.(recordedBlob);
      };

      recorder.start(1000); // Collect data every 1s
      startTimeRef.current = Date.now();
      setState("recording");

      // Timer for elapsed time display
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setElapsed(elapsed);

        // Auto-stop at max duration
        if (elapsed >= maxDuration) {
          recorder.stop();
        }
      }, 500);
    },
    [maxDuration, onStop]
  );

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    clearInterval(timerRef.current);
  }, []);

  const reset = useCallback(() => {
    setBlob(null);
    setElapsed(0);
    setState("idle");
    chunksRef.current = [];
    clearInterval(timerRef.current);
  }, []);

  const getDurationSeconds = useCallback(() => {
    if (startTimeRef.current) {
      return Math.floor((Date.now() - startTimeRef.current) / 1000);
    }
    return elapsed;
  }, [elapsed]);

  return {
    state,
    elapsed,
    blob,
    startRecording,
    stopRecording,
    reset,
    getDurationSeconds,
    remaining: Math.max(0, maxDuration - elapsed),
  };
}
