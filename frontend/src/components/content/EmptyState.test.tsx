import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  test("renders default message", () => {
    render(<EmptyState />);
    expect(
      screen.getByText("No content available for today. Check back later!"),
    ).toBeDefined();
  });

  test("renders custom message", () => {
    render(<EmptyState message="Nothing here yet" />);
    expect(screen.getByText("Nothing here yet")).toBeDefined();
  });
});
