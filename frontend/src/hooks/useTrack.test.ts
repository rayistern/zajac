import { renderHook, act } from "@testing-library/react";
import { describe, expect, test, beforeEach } from "vitest";
import { useTrack } from "./useTrack";

describe("useTrack", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("defaults to 3-perek", () => {
    const { result } = renderHook(() => useTrack());
    expect(result.current.track).toBe("3-perek");
  });

  test("reads stored preference from localStorage", () => {
    localStorage.setItem("merkos-rambam-track", "1-perek");
    const { result } = renderHook(() => useTrack());
    expect(result.current.track).toBe("1-perek");
  });

  test("sets track and persists to localStorage", () => {
    const { result } = renderHook(() => useTrack());
    act(() => {
      result.current.setTrack("1-perek");
    });
    expect(result.current.track).toBe("1-perek");
    expect(localStorage.getItem("merkos-rambam-track")).toBe("1-perek");
  });

  test("ignores invalid stored value", () => {
    localStorage.setItem("merkos-rambam-track", "invalid");
    const { result } = renderHook(() => useTrack());
    expect(result.current.track).toBe("3-perek");
  });
});
