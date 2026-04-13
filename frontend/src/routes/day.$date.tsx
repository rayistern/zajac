import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ContentFeed } from "../components/content/ContentFeed";
import { DayNavigator } from "../components/navigation/DayNavigator";
import { useTrack } from "../hooks/useTrack";

export const Route = createFileRoute("/day/$date")({
  component: DayPage,
});

function DayPage() {
  const { date } = Route.useParams();
  const { track } = useTrack();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["content", "day", date, track],
    queryFn: async () => {
      const res = await fetch(`/api/content/day/${date}?track=${track}`);
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch");
      return res.json();
    },
  });

  return (
    <div className="px-5 pt-5">
      {/* Header */}
      <header className="flex items-center justify-between mb-5">
        <button
          onClick={() => navigate({ to: "/" })}
          className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors"
        >
          <svg className="w-5 h-5 stroke-white fill-none" strokeWidth={2} strokeLinecap="round" viewBox="0 0 24 24">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="text-center flex-1">
          <div className="font-[family-name:var(--font-ui)] text-[10px] font-extrabold text-[var(--green)] uppercase tracking-[2px]">
            Daily Learning
          </div>
          <div className="font-[family-name:var(--font-ui)] text-sm font-bold">
            {data?.hebrewDate ?? date}
          </div>
        </div>
        <DayNavigator currentDate={date} />
      </header>

      {/* Content */}
      {isLoading ? (
        <div className="h-40 flex items-center justify-center text-[var(--grey-dim)]">
          Loading...
        </div>
      ) : data?.items?.length ? (
        <ContentFeed items={data.items} />
      ) : (
        <div className="h-40 flex items-center justify-center text-[var(--grey-dim)]">
          No content for {date}.
        </div>
      )}
    </div>
  );
}
