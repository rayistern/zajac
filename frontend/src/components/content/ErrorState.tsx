interface Props {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  message = "Something went wrong loading content.",
  onRetry,
}: Props) {
  return (
    <section
      className="flex flex-col items-center justify-center py-12 px-6 text-center"
      role="alert"
    >
      <div className="w-16 h-16 mb-5 rounded-full bg-[rgba(239,68,68,0.1)] flex items-center justify-center">
        <svg
          className="w-8 h-8 text-red-400"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
          />
        </svg>
      </div>
      <p className="font-[family-name:var(--font-body)] text-sm text-[var(--grey)] mb-4 max-w-[280px]">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-5 py-2.5 bg-[var(--elevated)] hover:bg-[var(--surface)] rounded-xl font-[family-name:var(--font-ui)] text-xs font-bold text-white transition-colors"
        >
          Try Again
        </button>
      )}
    </section>
  );
}
