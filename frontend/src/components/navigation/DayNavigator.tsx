import { useNavigate } from "@tanstack/react-router";

interface Props {
  currentDate: string;
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

export function DayNavigator({ currentDate }: Props) {
  const navigate = useNavigate();

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => navigate({ to: "/day/$date", params: { date: addDays(currentDate, -1) } })}
        className="w-8 h-8 rounded-full bg-[var(--elevated)] flex items-center justify-center hover:bg-white/10 transition-colors"
      >
        <svg className="w-4 h-4 stroke-[var(--grey)] fill-none" strokeWidth={2} strokeLinecap="round" viewBox="0 0 24 24">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <button
        onClick={() => navigate({ to: "/day/$date", params: { date: addDays(currentDate, 1) } })}
        className="w-8 h-8 rounded-full bg-[var(--elevated)] flex items-center justify-center hover:bg-white/10 transition-colors"
      >
        <svg className="w-4 h-4 stroke-[var(--grey)] fill-none" strokeWidth={2} strokeLinecap="round" viewBox="0 0 24 24">
          <polyline points="9 6 15 12 9 18" />
        </svg>
      </button>
    </div>
  );
}
