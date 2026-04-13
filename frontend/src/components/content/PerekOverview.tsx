interface Props {
  title: string;
  text: string;
  sefer: string;
  perek: number;
}

export function PerekOverview({ title, text }: Props) {
  return (
    <div className="bg-[var(--surface)] rounded-[20px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.3)]">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-[var(--elevated)] rounded-xl flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 stroke-[var(--grey)] fill-none" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
        </div>
        <div>
          <div className="font-[family-name:var(--font-ui)] text-[9px] font-extrabold uppercase tracking-[1.5px] text-[var(--grey-dim)]">
            Perek Overview
          </div>
          <div className="font-[family-name:var(--font-ui)] text-[15px] font-extrabold">
            {title}
          </div>
        </div>
      </div>
      <p className="font-[family-name:var(--font-body)] text-[13px] leading-[1.7] text-white/70">
        {text}
      </p>
    </div>
  );
}
