import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ConceptualImage } from "./ConceptualImage";

describe("ConceptualImage", () => {
  test("renders title and caption", () => {
    render(
      <ConceptualImage
        title="Temple Layout"
        caption="The structure of the Beis HaMikdash"
        imageUrl="https://example.com/temple.webp"
      />,
    );
    expect(screen.getByText("Temple Layout")).toBeDefined();
    expect(screen.getByText("The structure of the Beis HaMikdash")).toBeDefined();
  });

  test("renders halacha badge when provided", () => {
    render(
      <ConceptualImage
        title="Title"
        caption="Caption"
        imageUrl="https://example.com/img.webp"
        halachaStart={3}
      />,
    );
    expect(screen.getByText(/Halacha 3/)).toBeDefined();
  });

  test("renders illustration badge without halacha", () => {
    const { container } = render(
      <ConceptualImage
        title="Title"
        caption="Caption"
        imageUrl="https://example.com/img.webp"
      />,
    );
    expect(container.textContent).toContain("Illustration");
  });

  test("renders share button when id is provided", () => {
    const { container } = render(
      <ConceptualImage
        id="abc-123"
        title="Title"
        caption="Caption"
        imageUrl="https://example.com/img.webp"
      />,
    );
    expect(container.textContent).toContain("Share");
  });

  test("does not render share button when id is missing", () => {
    const { container } = render(
      <ConceptualImage
        title="Title"
        caption="Caption"
        imageUrl="https://example.com/img.webp"
      />,
    );
    expect(container.textContent).not.toContain("Share");
  });
});
