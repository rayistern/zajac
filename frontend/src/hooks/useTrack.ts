import { useState, useCallback } from "react";

type Track = "1-perek" | "3-perek";

const STORAGE_KEY = "merkos-rambam-track";

export function useTrack() {
  const [track, setTrackState] = useState<Track>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "1-perek" ? "1-perek" : "3-perek";
  });

  const setTrack = useCallback((t: Track) => {
    setTrackState(t);
    localStorage.setItem(STORAGE_KEY, t);
  }, []);

  return { track, setTrack } as const;
}
