import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ContentFeed } from "./ContentFeed";

const mockItems = [
  {
    id: "1",
    contentType: "perek_overview",
    sefer: "Shabbat",
    perek: 1,
    halachaStart: null,
    halachaEnd: null,
    title: "Introduction to Shabbat",
    content: { text: "The laws of Shabbat begin with..." },
    imageUrl: null,
    thumbnailUrl: null,
  },
  {
    id: "2",
    contentType: "conceptual_image",
    sefer: "Shabbat",
    perek: 1,
    halachaStart: 1,
    halachaEnd: 3,
    title: "Shabbat Boundaries",
    content: { caption: "A visual depiction" },
    imageUrl: "https://example.com/img.webp",
    thumbnailUrl: null,
  },
  {
    id: "3",
    contentType: "did_you_know",
    sefer: "Shabbat",
    perek: 1,
    halachaStart: null,
    halachaEnd: null,
    title: null,
    content: { text: "The Rambam lists 39 categories" },
    imageUrl: null,
    thumbnailUrl: null,
  },
];

describe("ContentFeed", () => {
  test("renders all content items", () => {
    render(<ContentFeed items={mockItems} />);
    expect(screen.getByText("Introduction to Shabbat")).toBeDefined();
    expect(screen.getByText("Shabbat Boundaries")).toBeDefined();
    expect(screen.getByText("The Rambam lists 39 categories")).toBeDefined();
  });

  test("renders perek overview with text", () => {
    render(
      <ContentFeed
        items={[
          {
            id: "1",
            contentType: "perek_overview",
            sefer: "Shabbat",
            perek: 1,
            halachaStart: null,
            halachaEnd: null,
            title: "My Overview",
            content: { text: "Overview body text" },
            imageUrl: null,
            thumbnailUrl: null,
          },
        ]}
      />,
    );
    expect(screen.getByText("My Overview")).toBeDefined();
    expect(screen.getByText("Overview body text")).toBeDefined();
  });

  test("renders empty feed without crashing", () => {
    render(<ContentFeed items={[]} />);
    // Should render the container div without errors
    expect(document.querySelector(".flex")).toBeDefined();
  });

  test("skips unknown content types", () => {
    render(
      <ContentFeed
        items={[
          {
            id: "1",
            contentType: "unknown_type",
            sefer: "Shabbat",
            perek: 1,
            halachaStart: null,
            halachaEnd: null,
            title: "Unknown",
            content: {},
            imageUrl: null,
            thumbnailUrl: null,
          },
        ]}
      />,
    );
    // Should render the container but no content card
    expect(screen.queryByText("Unknown")).toBeNull();
  });
});
