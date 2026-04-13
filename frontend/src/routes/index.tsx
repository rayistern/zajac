import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { TrackSelector } from "../components/navigation/TrackSelector";
import { ContentFeed } from "../components/content/ContentFeed";
import { SichosHighlight } from "../components/content/SichosHighlight";
import { HeroSkeleton, FeedSkeleton } from "../components/content/Skeleton";
import { EmptyState } from "../components/content/EmptyState";
import { ErrorState } from "../components/content/ErrorState";
import { useTrack } from "../hooks/useTrack";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function todayDate() {
  return new Date().toISOString().split("T")[0];
}

function HomePage() {
  const { track, setTrack } = useTrack();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["content", "today", track],
    queryFn: async () => {
      const res = await fetch(`/api/content/today?track=${track}`);
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch");
      return res.json();
    },
  });

  const { data: sichosData } = useQuery({
    queryKey: ["sichos", data?.items?.[0]?.sefer],
    queryFn: async () => {
      if (!data?.items?.[0]?.sefer) return [];
      const sefer = data.items[0].sefer;
      const perek = data.items[0].perek;
      const res = await fetch(`/api/sichos/${encodeURIComponent(sefer)}/${perek}`);
      if (!res.ok) return [];
      return res.json();
    },
    enabled: !!data?.items?.length,
  });

  const perakim = data?.perakim ?? [];
  const perakimLabel =
    perakim.length > 0
      ? perakim.map((p: any) => `${p.sefer} Ch. ${p.perek}`).join(", ")
      : "";

  return (
    <div className="px-5 pt-5">
      {/* Header */}
      <header className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-[var(--green)] rounded-[10px] flex items-center justify-center font-[family-name:var(--font-hebrew)] text-lg font-bold text-[var(--bg)]">
            &#x05E8;
          </div>
          <h1 className="font-[family-name:var(--font-ui)] text-xl font-extrabold">
            Rambam
          </h1>
        </div>
      </header>

      {/* Track Selector */}
      <TrackSelector track={track} onSelect={setTrack} />

      {/* Today's Hero */}
      {isLoading ? (
        <HeroSkeleton />
      ) : error ? (
        <ErrorState
          message="Could not load today's content."
          onRetry={() => refetch()}
        />
      ) : !data ? (
        <EmptyState />
      ) : (
        <section
          className="bg-[rgba(29,185,84,0.08)] border border-[rgba(29,185,84,0.12)] rounded-[20px] p-5 mb-6 relative overflow-hidden"
          aria-label="Today's Rambam learning"
        >
          <div className="absolute -top-10 -right-10 w-[120px] h-[120px] bg-[radial-gradient(circle,rgba(29,185,84,0.1),transparent_70%)] pointer-events-none" />
          <div className="flex items-center gap-1.5 font-[family-name:var(--font-ui)] text-[9px] font-extrabold uppercase tracking-[2px] text-[var(--green)] mb-2.5">
            <div
              className="w-1.5 h-1.5 bg-[var(--green)] rounded-full animate-pulse"
              aria-hidden="true"
            />
            TODAY'S RAMBAM
          </div>
          <p className="font-[family-name:var(--font-ui)] text-[11px] font-semibold text-[var(--grey)] mb-1.5">
            {data.hebrewDate ?? todayDate()}
          </p>
          <h2 className="font-[family-name:var(--font-ui)] text-[22px] font-extrabold mb-3 leading-tight">
            {perakimLabel || "Today's Learning"}
          </h2>
          <div className="flex items-center gap-4 mb-4 font-[family-name:var(--font-ui)] text-[11px] font-semibold text-[var(--grey)]">
            <span>{data.items?.length ?? 0} items</span>
            <span>{perakim.length} perakim</span>
          </div>
          <button
            className="inline-flex items-center gap-2 px-6 py-3 bg-[var(--green)] rounded-3xl font-[family-name:var(--font-ui)] text-[13px] font-bold text-[var(--bg)] shadow-[0_4px_16px_rgba(29,185,84,0.3)] hover:scale-[1.03] active:scale-[0.98] transition-transform focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)]"
            aria-label="Start today's learning"
          >
            <svg
              className="w-4 h-4 fill-[var(--bg)]"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Start Learning
          </button>
        </section>
      )}

      {/* Content Feed */}
      {isLoading ? (
        <section className="mb-6">
          <h3 className="font-[family-name:var(--font-ui)] text-base font-extrabold mb-3.5">
            Today's Content
          </h3>
          <FeedSkeleton />
        </section>
      ) : data?.items && data.items.length > 0 ? (
        <section className="mb-6">
          <h3 className="font-[family-name:var(--font-ui)] text-base font-extrabold mb-3.5">
            Today's Content
          </h3>
          <ContentFeed items={data.items} />
        </section>
      ) : null}

      {/* Sichos */}
      {sichosData && sichosData.length > 0 && (
        <section className="mb-6">
          <h3 className="font-[family-name:var(--font-ui)] text-base font-extrabold mb-3.5">
            The Rebbe's Insights
          </h3>
          <div className="flex flex-col gap-3">
            {sichosData.map((s: any) => (
              <SichosHighlight
                key={s.id}
                excerpt={s.excerpt ?? ""}
                excerptHe={s.excerptHe}
                sourceVolume={s.sourceVolume}
                sourcePage={s.sourcePage}
                halacha={s.halacha}
                perek={
                  data?.items?.find(
                    (i: any) => i.sefer === s.sefer && i.perek === s.perek,
                  )?.perek ?? s.perek ?? 1
                }
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
