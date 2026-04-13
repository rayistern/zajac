import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { Infographic } from "./Infographic";

describe("Infographic", () => {
  test("renders title and caption", () => {
    render(
      <Infographic
        title="Shabbat Timeline"
        caption="Key halachic times"
        imageUrl="https://example.com/info.webp"
      />,
    );
    expect(screen.getByText("Shabbat Timeline")).toBeDefined();
    expect(screen.getByText("Key halachic times")).toBeDefined();
  });

  test("renders infographic badge", () => {
    const { container } = render(
      <Infographic title="T" caption="C" imageUrl="https://example.com/i.webp" />,
    );
    expect(container.textContent).toContain("Infographic");
  });

  test("renders image with lazy loading", () => {
    render(
      <Infographic title="Info" caption="Cap" imageUrl="https://example.com/i.webp" />,
    );
    const img = screen.getByAltText("Info");
    expect(img.getAttribute("loading")).toBe("lazy");
  });
});
