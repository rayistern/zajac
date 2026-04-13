import { render, fireEvent } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

const mockNavigate = vi.fn();
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mockNavigate,
}));

import { DayNavigator } from "./DayNavigator";

describe("DayNavigator", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  test("renders prev and next buttons", () => {
    const { container } = render(<DayNavigator currentDate="2026-04-13" />);
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(2);
  });

  test("navigates to previous day on prev click", () => {
    const { container } = render(<DayNavigator currentDate="2026-04-13" />);
    const buttons = container.querySelectorAll("button");
    fireEvent.click(buttons[0]);
    expect(mockNavigate).toHaveBeenCalledWith({
      to: "/day/$date",
      params: { date: "2026-04-12" },
    });
  });

  test("navigates to next day on next click", () => {
    const { container } = render(<DayNavigator currentDate="2026-04-13" />);
    const buttons = container.querySelectorAll("button");
    fireEvent.click(buttons[1]);
    expect(mockNavigate).toHaveBeenCalledWith({
      to: "/day/$date",
      params: { date: "2026-04-14" },
    });
  });
});
