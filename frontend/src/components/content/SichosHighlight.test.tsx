import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { SichosHighlight } from "./SichosHighlight";

describe("SichosHighlight", () => {
  test("renders excerpt and source", () => {
    render(
      <SichosHighlight
        excerpt="The deeper meaning of Shabbat rest"
        sourceVolume="Likkutei Sichos Vol. 16"
        sourcePage="p. 234"
        halacha={1}
        perek={3}
      />,
    );
    expect(screen.getByText("The deeper meaning of Shabbat rest")).toBeDefined();
    expect(screen.getByText("Likkutei Sichos Vol. 16 p. 234")).toBeDefined();
  });

  test("renders perek and halacha reference", () => {
    const { container } = render(
      <SichosHighlight
        excerpt="Test"
        sourceVolume="Vol 1"
        halacha={5}
        perek={2}
      />,
    );
    expect(container.textContent).toContain("Perek 2");
    expect(container.textContent).toContain("Halacha 5");
  });

  test("renders Hebrew excerpt when provided", () => {
    render(
      <SichosHighlight
        excerpt="English excerpt"
        excerptHe="שביתה בשבת"
        sourceVolume="Vol 1"
        halacha={1}
        perek={1}
      />,
    );
    expect(screen.getByText("שביתה בשבת")).toBeDefined();
  });

  test("does not render Hebrew when not provided", () => {
    const { container } = render(
      <SichosHighlight
        excerpt="Only English"
        sourceVolume="Vol 1"
        halacha={1}
        perek={1}
      />,
    );
    const rtlElements = container.querySelectorAll("[dir='rtl']");
    expect(rtlElements.length).toBe(0);
  });

  test("renders source without page when not provided", () => {
    render(
      <SichosHighlight
        excerpt="Test"
        sourceVolume="Likkutei Sichos Vol. 16"
        halacha={1}
        perek={1}
      />,
    );
    expect(screen.getByText("Likkutei Sichos Vol. 16")).toBeDefined();
  });
});
