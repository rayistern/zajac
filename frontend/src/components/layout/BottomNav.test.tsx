import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

// Mock TanStack Router
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  useRouterState: () => "/",
}));

import { BottomNav } from "./BottomNav";

describe("BottomNav", () => {
  test("renders all three nav tabs", () => {
    render(<BottomNav />);
    expect(screen.getByText("Home")).toBeDefined();
    expect(screen.getByText("Search")).toBeDefined();
    expect(screen.getByText("Saved")).toBeDefined();
  });

  test("renders navigation element with aria label", () => {
    const { container } = render(<BottomNav />);
    expect(container.querySelector("[aria-label='Main navigation']")).toBeDefined();
  });

  test("renders three buttons", () => {
    const { container } = render(<BottomNav />);
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(3);
  });
});
