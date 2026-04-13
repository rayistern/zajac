import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { HeroSkeleton, FeedSkeleton, ContentCardSkeleton } from "./Skeleton";

describe("Skeleton components", () => {
  test("HeroSkeleton renders with aria label", () => {
    render(<HeroSkeleton />);
    expect(screen.getByLabelText("Loading today's content")).toBeDefined();
  });

  test("FeedSkeleton renders multiple card skeletons", () => {
    const { container } = render(<FeedSkeleton />);
    expect(screen.getByLabelText("Loading content")).toBeDefined();
    const presentations = container.querySelectorAll("[role='presentation']");
    expect(presentations.length).toBeGreaterThanOrEqual(3);
  });

  test("ContentCardSkeleton renders", () => {
    const { container } = render(<ContentCardSkeleton />);
    expect(container.querySelector("[role='presentation']")).toBeDefined();
  });
});
