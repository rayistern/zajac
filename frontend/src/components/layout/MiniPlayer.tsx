import { useAudioPlayer } from "../../hooks/useAudioPlayer";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function MiniPlayer() {
  const { url, title, subtitle, isPlaying, currentTime, duration, toggle } =
    useAudioPlayer();

  if (!url) return null;

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      className="fixed bottom-[calc(var(--nav-height)+var(--safe-bottom))] left-2 right-2 z-[199] bg-[var(--surface)] rounded-[14px] px-3.5 py-2.5 flex items-center gap-3 shadow-[0_8px_32px_rgba(0,0,0,0.5)] border border-[var(--divider)]"
      role="region"
      aria-label="Audio player"
    >
      {/* Art */}
      <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[var(--elevated)] to-[#1a2020] flex items-center justify-center shrink-0 text-xl opacity-50">
        &#x1F3DB;
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="font-[family-name:var(--font-ui)] text-xs font-bold truncate">
          {title}
        </div>
        <div className="font-[family-name:var(--font-body)] text-[10px] text-[var(--grey-dim)]">
          {subtitle} &middot; {formatTime(currentTime)} / {formatTime(duration)}
        </div>
      </div>

      {/* Play/Pause */}
      <button
        onClick={toggle}
        aria-label={isPlaying ? "Pause" : "Play"}
        className="w-9 h-9 bg-white rounded-full flex items-center justify-center shrink-0"
      >
        {isPlaying ? (
          <svg className="w-3.5 h-3.5 fill-[var(--bg)]" viewBox="0 0 24 24">
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 fill-[var(--bg)] ml-0.5" viewBox="0 0 24 24">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        )}
      </button>

      {/* Progress bar */}
      <div className="absolute bottom-0 left-3.5 right-3.5 h-0.5 bg-[var(--elevated)] rounded-sm">
        <div
          className="h-full bg-[var(--green)] rounded-sm transition-[width] duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
