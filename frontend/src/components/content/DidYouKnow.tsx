interface Props {
  text: string;
}

export function DidYouKnow({ text }: Props) {
  return (
    <div className="bg-gradient-to-br from-[var(--elevated)] to-[rgba(40,40,40,0.6)] border border-white/5 rounded-[20px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.3)] relative overflow-hidden">
      <div className="absolute -top-5 -right-5 w-20 h-20 bg-[radial-gradient(circle,rgba(179,157,219,0.08),transparent_70%)] pointer-events-none" />
      <div className="flex items-center gap-1.5 font-[family-name:var(--font-ui)] text-[9px] font-extrabold uppercase tracking-[2px] text-[#B39DDB] mb-2.5">
        <div className="w-[18px] h-[18px] bg-[rgba(179,157,219,0.15)] rounded-[5px] flex items-center justify-center">
          <svg className="w-[11px] h-[11px] stroke-[#B39DDB] fill-none" strokeWidth={2} strokeLinecap="round" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        </div>
        Did You Know
      </div>
      <p className="font-[family-name:var(--font-body)] text-[14px] font-medium leading-[1.65] text-white/85">
        {text}
      </p>
    </div>
  );
}
