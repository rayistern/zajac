interface Props {
  track: "1-perek" | "3-perek";
  onSelect: (t: "1-perek" | "3-perek") => void;
}

export function TrackSelector({ track, onSelect }: Props) {
  return (
    <div className="flex gap-2 mb-6">
      {(["3-perek", "1-perek"] as const).map((t) => (
        <button
          key={t}
          onClick={() => onSelect(t)}
          className={`flex-1 px-4 py-2.5 rounded-xl text-center transition-all border-[1.5px] ${
            track === t
              ? "bg-[var(--green-dim)] border-[var(--green-border)]"
              : "bg-[var(--surface)] border-transparent"
          }`}
        >
          <div
            className={`font-[family-name:var(--font-ui)] text-[11px] font-extrabold uppercase tracking-wider mb-0.5 ${
              track === t ? "text-[var(--green)]" : "text-[var(--grey-dim)]"
            }`}
          >
            {t === "3-perek" ? "3 Perakim" : "1 Perek"}
          </div>
        </button>
      ))}
    </div>
  );
}
