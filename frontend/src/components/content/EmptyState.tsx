interface Props {
  message?: string;
}

export function EmptyState({
  message = "No content available for today. Check back later!",
}: Props) {
  return (
    <section className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-20 h-20 mb-6 rounded-full bg-[var(--elevated)] flex items-center justify-center text-4xl opacity-40">
        📖
      </div>
      <p className="font-[family-name:var(--font-body)] text-sm text-[var(--grey)] leading-relaxed max-w-[280px]">
        {message}
      </p>
    </section>
  );
}
