interface Props {
  contentId: string;
  title: string;
}

export function ShareButton({ contentId, title }: Props) {
  async function handleShare() {
    const shareUrl = `${window.location.origin}/api/share/${contentId}/meta`;
    const shareData = {
      title: `Merkos Rambam — ${title}`,
      text: title,
      url: shareUrl,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch {
        // User cancelled
      }
    } else {
      await navigator.clipboard.writeText(shareUrl);
    }
  }

  return (
    <button
      onClick={handleShare}
      className="inline-flex items-center gap-1 mt-2 font-[family-name:var(--font-ui)] text-[10px] font-bold text-[var(--green)] opacity-70 hover:opacity-100 transition-opacity"
    >
      <svg
        className="w-3 h-3 stroke-[var(--green)] fill-none"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        viewBox="0 0 24 24"
      >
        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
        <polyline points="16 6 12 2 8 6" />
        <line x1="12" y1="2" x2="12" y2="15" />
      </svg>
      Share
    </button>
  );
}
