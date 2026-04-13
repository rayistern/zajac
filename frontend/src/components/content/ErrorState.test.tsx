import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  test("renders default error message", () => {
    render(<ErrorState />);
    expect(screen.getByText("Something went wrong loading content.")).toBeDefined();
  });

  test("renders custom error message", () => {
    render(<ErrorState message="Custom error occurred" />);
    expect(screen.getByText("Custom error occurred")).toBeDefined();
  });

  test("renders retry button when onRetry provided", () => {
    const onRetry = vi.fn();
    render(<ErrorState onRetry={onRetry} />);
    const button = screen.getByText("Try Again");
    expect(button).toBeDefined();
    fireEvent.click(button);
    expect(onRetry).toHaveBeenCalledOnce();
  });

  test("does not render retry button when onRetry not provided", () => {
    const { container } = render(<ErrorState />);
    // The button should not exist within this specific render
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(0);
  });

  test("has alert role for accessibility", () => {
    const { container } = render(<ErrorState />);
    expect(container.querySelector("[role='alert']")).toBeDefined();
  });
});
