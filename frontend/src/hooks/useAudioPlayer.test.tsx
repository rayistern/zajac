import { renderHook, act } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";
import { AudioPlayerProvider, useAudioPlayer } from "./useAudioPlayer";
import type { ReactNode } from "react";

// Mock HTMLAudioElement
class MockAudio {
  src = "";
  currentTime = 0;
  duration = 0;
  paused = true;
  listeners: Record<string, Function[]> = {};

  addEventListener(event: string, handler: Function) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(handler);
  }

  play() {
    this.paused = false;
    return Promise.resolve();
  }

  pause() {
    this.paused = true;
  }
}

beforeEach(() => {
  vi.stubGlobal("Audio", MockAudio);
});

function wrapper({ children }: { children: ReactNode }) {
  return <AudioPlayerProvider>{children}</AudioPlayerProvider>;
}

describe("useAudioPlayer", () => {
  test("throws when used outside provider", () => {
    expect(() => {
      renderHook(() => useAudioPlayer());
    }).toThrow("useAudioPlayer must be inside AudioPlayerProvider");
  });

  test("returns initial state", () => {
    const { result } = renderHook(() => useAudioPlayer(), { wrapper });
    expect(result.current.url).toBeNull();
    expect(result.current.title).toBe("");
    expect(result.current.subtitle).toBe("");
    expect(result.current.isPlaying).toBe(false);
    expect(result.current.currentTime).toBe(0);
    expect(result.current.duration).toBe(0);
  });

  test("play sets url, title, subtitle and isPlaying", () => {
    const { result } = renderHook(() => useAudioPlayer(), { wrapper });
    act(() => {
      result.current.play("https://example.com/audio.mp3", "Perek 1", "Shabbat");
    });
    expect(result.current.url).toBe("https://example.com/audio.mp3");
    expect(result.current.title).toBe("Perek 1");
    expect(result.current.subtitle).toBe("Shabbat");
    expect(result.current.isPlaying).toBe(true);
  });

  test("toggle pauses when playing", () => {
    const { result } = renderHook(() => useAudioPlayer(), { wrapper });
    act(() => {
      result.current.play("https://example.com/audio.mp3", "T", "S");
    });
    act(() => {
      result.current.toggle();
    });
    expect(result.current.isPlaying).toBe(false);
  });

  test("toggle does nothing when no audio loaded", () => {
    const { result } = renderHook(() => useAudioPlayer(), { wrapper });
    act(() => {
      result.current.toggle();
    });
    expect(result.current.isPlaying).toBe(false);
  });

  test("seek does nothing when no audio loaded", () => {
    const { result } = renderHook(() => useAudioPlayer(), { wrapper });
    expect(() => {
      act(() => {
        result.current.seek(30);
      });
    }).not.toThrow();
  });
});
