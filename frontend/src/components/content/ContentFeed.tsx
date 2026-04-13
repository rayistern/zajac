import { PerekOverview } from "./PerekOverview";
import { ConceptualImage } from "./ConceptualImage";
import { Infographic } from "./Infographic";
import { DailyChart } from "./DailyChart";
import { DidYouKnow } from "./DidYouKnow";

interface ContentItem {
  id: string;
  contentType: string;
  sefer: string;
  perek: number;
  halachaStart?: number | null;
  halachaEnd?: number | null;
  title?: string | null;
  content: any;
  imageUrl?: string | null;
  thumbnailUrl?: string | null;
}

interface Props {
  items: ContentItem[];
}

export function ContentFeed({ items }: Props) {
  return (
    <div className="flex flex-col gap-3.5">
      {items.map((item) => (
        <ContentCard key={item.id} item={item} />
      ))}
    </div>
  );
}

function ContentCard({ item }: { item: ContentItem }) {
  switch (item.contentType) {
    case "perek_overview":
      return (
        <PerekOverview
          title={item.title ?? "Overview"}
          text={item.content?.text ?? ""}
          sefer={item.sefer}
          perek={item.perek}
        />
      );

    case "conceptual_image":
      return (
        <ConceptualImage
          id={item.id}
          title={item.title ?? ""}
          caption={item.content?.caption ?? ""}
          imageUrl={item.imageUrl ?? ""}
          halachaStart={item.halachaStart}
          halachaEnd={item.halachaEnd}
        />
      );

    case "infographic":
      return (
        <Infographic
          title={item.title ?? ""}
          caption={item.content?.caption ?? ""}
          imageUrl={item.imageUrl ?? ""}
        />
      );

    case "daily_chart":
      return (
        <DailyChart
          title={item.title ?? ""}
          caption={item.content?.caption ?? ""}
          imageUrl={item.imageUrl ?? ""}
        />
      );

    case "did_you_know":
      return <DidYouKnow text={item.content?.text ?? ""} />;

    default:
      return null;
  }
}
