import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";
import { ShareButton } from "./ShareButton";

describe("ShareButton", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "share", { value: undefined, writable: true, configurable: true });
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      writable: true,
      configurable: true,
    });
  });

  test("renders share button with text", () => {
    render(<ShareButton contentId="abc-123" title="Test Title" />);
    expect(screen.getByText("Share")).toBeDefined();
  });

  test("renders SVG icon", () => {
    const { container } = render(<ShareButton contentId="abc-123" title="Test" />);
    expect(container.querySelector("svg")).not.toBeNull();
  });

  test("copies to clipboard when navigator.share unavailable", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
      configurable: true,
    });

    const { container } = render(<ShareButton contentId="test-id" title="Test" />);
    const btn = container.querySelector("button")!;
    await fireEvent.click(btn);

    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        expect.stringContaining("/api/share/test-id/meta"),
      );
    });
  });

  test("uses navigator.share when available", async () => {
    const shareFn = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", {
      value: shareFn,
      writable: true,
      configurable: true,
    });

    const { container } = render(<ShareButton contentId="share-id" title="Share Title" />);
    const btn = container.querySelector("button")!;
    await fireEvent.click(btn);

    await vi.waitFor(() => {
      expect(shareFn).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Merkos Rambam — Share Title" }),
      );
    });
  });
});
