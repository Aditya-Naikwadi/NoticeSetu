"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Pause, Play, RotateCcw, Volume2 } from "lucide-react";
import { getAudioUrl, type LanguageCode } from "@/lib/api";

interface AudioPlayerProps {
  noticeHash: string;
  lang: LanguageCode;
  voiceScript: string;
}

const LANG_LABEL: Record<LanguageCode, string> = {
  en: "English Voice Brief",
  hi: "हिंदी वॉइस ब्रीफ",
  mr: "मराठी व्हॉईस ब्रीफ",
};

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function AudioPlayer({ noticeHash, lang, voiceScript }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [retryNonce, setRetryNonce] = useState(0);

  const audioSrc = `${getAudioUrl(noticeHash, lang)}?v=${retryNonce}`;

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    setIsPlaying(false);
    setIsLoading(false);
    setErrorMessage(null);
    setCurrentTime(0);
    setDuration(0);
  }, [lang, noticeHash]);

  async function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;

    if (errorMessage) {
      setErrorMessage(null);
      setRetryNonce((prev) => prev + 1);
      return;
    }

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage(null);
      await audio.play();
      setIsPlaying(true);
    } catch {
      setIsPlaying(false);
      setErrorMessage("Voice brief unavailable right now — tap to retry");
    } finally {
      setIsLoading(false);
    }
  }

  function handleSeek(event: React.ChangeEvent<HTMLInputElement>) {
    const audio = audioRef.current;
    if (!audio) return;
    const nextTime = Number(event.target.value);
    audio.currentTime = nextTime;
    setCurrentTime(nextTime);
  }

  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-3.5">
      <audio
        ref={audioRef}
        src={audioSrc}
        preload="none"
        onLoadedMetadata={() => {
          if (audioRef.current) setDuration(audioRef.current.duration || 0);
        }}
        onTimeUpdate={() => {
          if (audioRef.current) setCurrentTime(audioRef.current.currentTime || 0);
        }}
        onEnded={() => {
          setIsPlaying(false);
          setCurrentTime(0);
        }}
        onError={() => {
          setIsPlaying(false);
          setIsLoading(false);
          setErrorMessage("Voice brief unavailable right now — tap to retry");
        }}
      />

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={togglePlay}
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-600 text-white shadow-sm transition hover:bg-teal-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900"
          aria-label={isPlaying ? "Pause voice brief" : "Play voice brief"}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : errorMessage ? (
            <RotateCcw className="h-4 w-4" />
          ) : isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 pl-0.5" />
          )}
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2 text-xs font-semibold text-slate-800">
            <span className="inline-flex items-center gap-1.5">
              <Volume2 className="h-3.5 w-3.5 text-teal-700" />
              {LANG_LABEL[lang]}
            </span>
            <span className="tabular-nums text-slate-600">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          <input
            type="range"
            min={0}
            max={duration > 0 ? duration : 100}
            value={duration > 0 ? currentTime : 0}
            onChange={handleSeek}
            disabled={duration <= 0}
            aria-label="Audio progress"
            className="mt-1.5 h-1.5 w-full cursor-pointer accent-teal-600 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      {errorMessage ? (
        <p className="mt-2 text-xs font-medium text-amber-800">{errorMessage}</p>
      ) : (
        <p className="mt-2 text-xs text-slate-600">{voiceScript}</p>
      )}
    </div>
  );
}

