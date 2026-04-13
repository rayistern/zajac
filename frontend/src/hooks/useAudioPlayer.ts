import { createContext, useContext, useRef, useState, useCallback } from "react";
import type { ReactNode } from "react";
import React from "react";

interface AudioState {
  url: string | null;
  title: string;
  subtitle: string;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
}

interface AudioActions {
  play: (url: string, title: string, subtitle: string) => void;
  toggle: () => void;
  seek: (time: number) => void;
}

type AudioContextType = AudioState & AudioActions;

const AudioContext = createContext<AudioContextType | null>(null);

export function AudioPlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<AudioState>({
    url: null,
    title: "",
    subtitle: "",
    isPlaying: false,
    currentTime: 0,
    duration: 0,
  });

  const play = useCallback((url: string, title: string, subtitle: string) => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.addEventListener("timeupdate", () => {
        setState((s) => ({
          ...s,
          currentTime: audioRef.current?.currentTime ?? 0,
        }));
      });
      audioRef.current.addEventListener("loadedmetadata", () => {
        setState((s) => ({
          ...s,
          duration: audioRef.current?.duration ?? 0,
        }));
      });
      audioRef.current.addEventListener("ended", () => {
        setState((s) => ({ ...s, isPlaying: false }));
      });
    }
    audioRef.current.src = url;
    audioRef.current.play();
    setState((s) => ({ ...s, url, title, subtitle, isPlaying: true }));
  }, []);

  const toggle = useCallback(() => {
    if (!audioRef.current) return;
    if (audioRef.current.paused) {
      audioRef.current.play();
      setState((s) => ({ ...s, isPlaying: true }));
    } else {
      audioRef.current.pause();
      setState((s) => ({ ...s, isPlaying: false }));
    }
  }, []);

  const seek = useCallback((time: number) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = time;
  }, []);

  return React.createElement(
    AudioContext.Provider,
    { value: { ...state, play, toggle, seek } },
    children,
  );
}

export function useAudioPlayer() {
  const ctx = useContext(AudioContext);
  if (!ctx) throw new Error("useAudioPlayer must be inside AudioPlayerProvider");
  return ctx;
}
