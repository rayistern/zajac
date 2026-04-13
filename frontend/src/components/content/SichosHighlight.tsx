interface Props {
  excerpt: string;
  excerptHe?: string | null;
  sourceVolume: string;
  sourcePage?: string | null;
  halacha: number;
  perek: number;
}

export function SichosHighlight({
  excerpt,
  excerptHe,
  sourceVolume,
  sourcePage,
  halacha,
  perek,
}: Props) {
  return (
    <div className="bg-[rgba(197,160,89,0.06)] border border-[rgba(197,160,89,0.12)] rounded-[20px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.3)]">
      <div className="flex items-center gap-1.5 font-[family-name:var(--font-ui)] text-[9px] font-extrabold uppercase tracking-[1.5px] text-[var(--gold)] mb-2.5">
        <div className="w-[5px] h-[5px] bg-[var(--gold)] rounded-full" />
        The Rebbe's Insight &middot; Perek {perek}, Halacha {halacha}
      </div>
      <p className="font-[family-name:var(--font-body)] text-[13px] leading-[1.7] text-white/75 mb-2">
        {excerpt}
      </p>
      {excerptHe && (
        <p
          className="font-[family-name:var(--font-hebrew)] text-[12px] text-[rgba(197,160,89,0.5)] mb-1"
          dir="rtl"
        >
          {excerptHe}
        </p>
      )}
      <p className="font-[family-name:var(--font-ui)] text-[11px] font-semibold text-[rgba(197,160,89,0.6)]">
        {sourceVolume}
        {sourcePage ? ` ${sourcePage}` : ""}
      </p>
    </div>
  );
}
