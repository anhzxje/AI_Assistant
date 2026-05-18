"use client";

import { useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";

type VoiceMode = "push_to_talk" | "auto_stop";
type VoiceState = "idle" | "listening" | "speaking" | "waiting" | "processing";

export function VoiceRecorderButton({
  disabled,
  processing,
  onAudioReady,
  onError
}: {
  disabled?: boolean;
  processing?: boolean;
  onAudioReady: (audio: Blob, voiceMode?: VoiceMode) => Promise<void> | void;
  onError: (message: string) => void;
}) {
  const [voiceMode, setVoiceMode] = useState<VoiceMode>("auto_stop");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationRef = useRef<number | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const startedAtRef = useRef(0);
  const speechStartedRef = useRef(false);
  const lastSpeechAtRef = useRef(0);

  async function toggleRecording() {
    if (voiceState !== "idle") {
      stopRecording();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      streamRef.current = stream;
      chunksRef.current = [];
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        cleanupAudioGraph();
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        setVoiceState("processing");
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        void Promise.resolve(onAudioReady(blob, voiceMode)).finally(() => setVoiceState("idle"));
      };
      startedAtRef.current = Date.now();
      speechStartedRef.current = false;
      lastSpeechAtRef.current = Date.now();
      setVoiceState("listening");
      recorder.start();
      if (voiceMode === "auto_stop") {
        startAutoStopMonitor(stream);
      }
    } catch (err) {
      setVoiceState("idle");
      onError(err instanceof Error ? err.message : "Microphone is unavailable");
    }
  }

  const isDisabled = disabled || processing;
  const recording = voiceState === "listening" || voiceState === "speaking" || voiceState === "waiting";

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    } else {
      cleanupAudioGraph();
      setVoiceState("idle");
    }
  }

  function startAutoStopMonitor(stream: MediaStream) {
    const AudioContextCtor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextCtor) return;
    const audioContext = new AudioContextCtor();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    audioContextRef.current = audioContext;
    const data = new Uint8Array(analyser.fftSize);
    const silenceMs = 1200;
    const minRecordingMs = 700;
    const maxRecordingMs = 20000;
    const preSpeechGraceMs = 3000;
    const threshold = 0.035;

    function tick() {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (const value of data) {
        const centered = (value - 128) / 128;
        sum += centered * centered;
      }
      const rms = Math.sqrt(sum / data.length);
      const now = Date.now();
      const elapsed = now - startedAtRef.current;
      if (rms > threshold) {
        speechStartedRef.current = true;
        lastSpeechAtRef.current = now;
        setVoiceState("speaking");
      } else if (speechStartedRef.current) {
        setVoiceState("waiting");
      }

      if (!speechStartedRef.current && elapsed > preSpeechGraceMs) {
        onError("Mình chưa nghe rõ, bạn thử nói lại nhé.");
        stopRecording();
        return;
      }
      if (speechStartedRef.current && elapsed > minRecordingMs && now - lastSpeechAtRef.current > silenceMs) {
        stopRecording();
        return;
      }
      if (elapsed > maxRecordingMs) {
        stopRecording();
        return;
      }
      animationRef.current = requestAnimationFrame(tick);
    }
    animationRef.current = requestAnimationFrame(tick);
  }

  function cleanupAudioGraph() {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    void audioContextRef.current?.close();
    audioContextRef.current = null;
  }

  const statusText =
    voiceState === "speaking"
      ? "Speaking"
      : voiceState === "waiting"
        ? "Waiting"
        : voiceState === "listening"
          ? "Listening"
          : voiceState === "processing"
            ? "Processing"
            : voiceMode === "auto_stop"
              ? "Auto"
              : "Voice";

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => setVoiceMode((mode) => (mode === "auto_stop" ? "push_to_talk" : "auto_stop"))}
        disabled={recording || isDisabled}
        title={voiceMode === "auto_stop" ? "Auto detect stop" : "Push to talk"}
        className="focus-ring hidden h-9 shrink-0 items-center justify-center rounded-md border border-line px-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 sm:inline-flex"
      >
        {voiceMode === "auto_stop" ? "Auto" : "Push"}
      </button>
      <button
        type="button"
        onClick={toggleRecording}
        disabled={isDisabled}
        title={recording ? "Stop recording" : "Record voice"}
        className={`focus-ring inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300 ${
          recording ? "bg-red-600 hover:bg-red-700" : "bg-slate-800 hover:bg-slate-900"
        }`}
      >
        {processing || voiceState === "processing" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : recording ? (
          <Square className="h-4 w-4" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
        <span className="hidden sm:inline">{recording ? statusText : statusText}</span>
      </button>
    </div>
  );
}
