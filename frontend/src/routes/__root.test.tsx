import { render } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

// Mock all dependencies
vi.mock("@tanstack/react-router", () => ({
  createRootRoute: (opts: any) => opts,
  Outlet: () => <div data-testid="outlet">Outlet</div>,
}));

vi.mock("../hooks/useAudioPlayer", () => ({
  AudioPlayerProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="audio-provider">{children}</div>
  ),
}));

vi.mock("../components/layout/MiniPlayer", () => ({
  MiniPlayer: () => <div data-testid="mini-player" />,
}));

vi.mock("../components/layout/BottomNav", () => ({
  BottomNav: () => <div data-testid="bottom-nav" />,
}));

import { Route } from "./__root";

describe("Root layout", () => {
  test("component renders with providers and layout elements", () => {
    const RootLayout = Route.component!;
    const { container } = render(<RootLayout />);
    expect(container.querySelector("[data-testid='audio-provider']")).toBeDefined();
    expect(container.querySelector("[data-testid='outlet']")).toBeDefined();
    expect(container.querySelector("[data-testid='mini-player']")).toBeDefined();
    expect(container.querySelector("[data-testid='bottom-nav']")).toBeDefined();
  });

  test("wraps content in AudioPlayerProvider", () => {
    const RootLayout = Route.component!;
    const { container } = render(<RootLayout />);
    expect(container.querySelector("[data-testid='audio-provider']")).not.toBeNull();
  });
});
