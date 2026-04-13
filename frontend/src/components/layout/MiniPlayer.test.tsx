import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

// Mock the useAudioPlayer hook
vi.mock("../../hooks/useAudioPlayer", () => ({
  useAudioPlayer: vi.fn(),
}));

import { MiniPlayer } from "./MiniPlayer";
import { useAudioPlayer } from "../../hooks/useAudioPlayer";

const mockUseAudioPlayer = vi.mocked(useAudioPlayer);

describe("MiniPlayer", () => {
  test("renders nothing when no url", () => {
    mockUseAudioPlayer.mockReturnValue({
      url: null,
      title: "",
      subtitle: "",
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      toggle: vi.fn(),
      play: vi.fn(),
      seek: vi.fn(),
    });
    const { container } = render(<MiniPlayer />);
    expect(container.innerHTML).toBe("");
  });

  test("renders player when url is set", () => {
    mockUseAudioPlayer.mockReturnValue({
      url: "https://example.com/audio.mp3",
      title: "Perek 1",
      subtitle: "Shabbat",
      isPlaying: false,
      currentTime: 30,
      duration: 120,
      toggle: vi.fn(),
      play: vi.fn(),
      seek: vi.fn(),
    });
    render(<MiniPlayer />);
    expect(screen.getByText("Perek 1")).toBeDefined();
    expect(screen.getByLabelText("Play")).toBeDefined();
  });

  test("shows pause button when playing", () => {
    mockUseAudioPlayer.mockReturnValue({
      url: "https://example.com/audio.mp3",
      title: "Perek 1",
      subtitle: "Shabbat",
      isPlaying: true,
      currentTime: 30,
      duration: 120,
      toggle: vi.fn(),
      play: vi.fn(),
      seek: vi.fn(),
    });
    render(<MiniPlayer />);
    expect(screen.getByLabelText("Pause")).toBeDefined();
  });

  test("displays formatted time", () => {
    mockUseAudioPlayer.mockReturnValue({
      url: "https://example.com/audio.mp3",
      title: "T",
      subtitle: "S",
      isPlaying: false,
      currentTime: 65,
      duration: 180,
      toggle: vi.fn(),
      play: vi.fn(),
      seek: vi.fn(),
    });
    const { container } = render(<MiniPlayer />);
    expect(container.textContent).toContain("1:05");
    expect(container.textContent).toContain("3:00");
  });
});
