import { ShareButton } from "../share/ShareButton";

interface Props {
  id?: string;
  title: string;
  caption: string;
  imageUrl: string;
  halachaStart?: number | null;
  halachaEnd?: number | null;
}

export function ConceptualImage({ id, title, caption, imageUrl, halachaStart }: Props) {
  return (
    <div className="rounded-[20px] overflow-hidden bg-[var(--surface)] shadow-[0_2px_8px_rgba(0,0,0,0.3)]">
      <div className="relative aspect-[16/10] bg-[var(--elevated)]">
        <img
          src={imageUrl}
          alt={title}
          className="w-full h-full object-cover"
          loading="lazy"
        />
        <div className="absolute top-2.5 left-2.5 px-2 py-1 rounded-md bg-[rgba(29,185,84,0.2)] font-[family-name:var(--font-ui)] text-[8px] font-extrabold uppercase tracking-wider text-[var(--green)]">
          Illustration{halachaStart ? ` · Halacha ${halachaStart}` : ""}
        </div>
      </div>
      <div className="p-4">
        <h4 className="font-[family-name:var(--font-ui)] text-[14px] font-bold mb-1">
          {title}
        </h4>
        <p className="font-[family-name:var(--font-body)] text-[12px] leading-[1.6] text-white/60">
          {caption}
        </p>
        {id && <ShareButton contentId={id} title={title} />}
      </div>
    </div>
  );
}
