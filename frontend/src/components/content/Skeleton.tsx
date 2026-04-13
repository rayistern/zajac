interface SkeletonProps {
  className?: string;
}

function Shimmer({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-[var(--elevated)] rounded-lg ${className}`}
      role="presentation"
    />
  );
}

export function HeroSkeleton() {
  return (
    <section
      className="bg-[rgba(29,185,84,0.04)] border border-[rgba(29,185,84,0.08)] rounded-[20px] p-5 mb-6"
      aria-label="Loading today's content"
    >
      <Shimmer className="w-28 h-3 mb-4" />
      <Shimmer className="w-20 h-3 mb-3" />
      <Shimmer className="w-48 h-6 mb-3" />
      <div className="flex gap-4 mb-4">
        <Shimmer className="w-16 h-3" />
        <Shimmer className="w-16 h-3" />
      </div>
      <Shimmer className="w-36 h-10 rounded-3xl" />
    </section>
  );
}

export function ContentCardSkeleton() {
  return (
    <div
      className="rounded-[20px] overflow-hidden bg-[var(--surface)]"
      role="presentation"
    >
      <Shimmer className="aspect-[16/10] rounded-none" />
      <div className="p-4">
        <Shimmer className="w-3/4 h-4 mb-2" />
        <Shimmer className="w-full h-3 mb-1" />
        <Shimmer className="w-2/3 h-3" />
      </div>
    </div>
  );
}

export function FeedSkeleton() {
  return (
    <div className="flex flex-col gap-3.5" aria-label="Loading content">
      <ContentCardSkeleton />
      <ContentCardSkeleton />
      <ContentCardSkeleton />
    </div>
  );
}
