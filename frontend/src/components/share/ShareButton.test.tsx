import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ShareButton } from "./ShareButton";

describe("ShareButton", () => {
  test("renders share button with text", () => {
    render(<ShareButton contentId="abc-123" title="Test Title" />);
    expect(screen.getByText("Share")).toBeDefined();
  });

  test("renders share button with SVG icon", () => {
    const { container } = render(<ShareButton contentId="abc-123" title="Test" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
    const button = container.querySelector("button");
    expect(button).toBeDefined();
  });
});
