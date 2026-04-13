import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { TrackSelector } from "./TrackSelector";

describe("TrackSelector", () => {
  test("renders both track options", () => {
    render(<TrackSelector track="3-perek" onSelect={() => {}} />);
    expect(screen.getByText("3 Perakim")).toBeDefined();
    expect(screen.getByText("1 Perek")).toBeDefined();
  });

  test("highlights active track", () => {
    const { container } = render(
      <TrackSelector track="1-perek" onSelect={() => {}} />,
    );
    const buttons = container.querySelectorAll("button");
    // 1-perek button should have green styling
    const onePerekButton = Array.from(buttons).find((b) =>
      b.textContent?.includes("1 Perek"),
    );
    expect(onePerekButton?.className).toContain("bg-[var(--green-dim)]");
  });

  test("calls onSelect when track is clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(<TrackSelector track="3-perek" onSelect={onSelect} />);
    const buttons = container.querySelectorAll("button");
    // "1 Perek" is the second button (order is 3-perek, 1-perek)
    const onePerekBtn = Array.from(buttons).find((b) => b.textContent?.includes("1 Perek"));
    fireEvent.click(onePerekBtn!);
    expect(onSelect).toHaveBeenCalledWith("1-perek");
  });
});
