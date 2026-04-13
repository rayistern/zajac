import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { DailyChart } from "./DailyChart";

describe("DailyChart", () => {
  test("renders title and caption", () => {
    render(
      <DailyChart
        title="Shabbat Melachot Distribution"
        caption="39 categories of forbidden work"
        imageUrl="https://example.com/chart.webp"
      />,
    );
    expect(screen.getByText("Shabbat Melachot Distribution")).toBeDefined();
    expect(screen.getByText("39 categories of forbidden work")).toBeDefined();
  });

  test("renders image with alt text", () => {
    render(
      <DailyChart
        title="My Chart"
        caption="Caption"
        imageUrl="https://example.com/chart.webp"
      />,
    );
    const img = screen.getByAltText("My Chart");
    expect(img).toBeDefined();
    expect(img.getAttribute("src")).toBe("https://example.com/chart.webp");
  });

  test("renders chart badge", () => {
    const { container } = render(
      <DailyChart title="Title" caption="Cap" imageUrl="https://example.com/c.webp" />,
    );
    expect(container.textContent).toContain("Chart");
  });
});
