import { useNavigate, useRouterState } from "@tanstack/react-router";

const tabs = [
  {
    label: "Home",
    path: "/",
    icon: (
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    ),
    iconExtra: <polyline points="9 22 9 12 15 12 15 22" />,
  },
  {
    label: "Search",
    path: "/search",
    icon: (
      <>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </>
    ),
  },
  {
    label: "Saved",
    path: "/saved",
    icon: (
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    ),
  },
];

export function BottomNav() {
  const navigate = useNavigate();
  const location = useRouterState({ select: (s) => s.location.pathname });

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-[200] bg-[var(--glass-heavy)] backdrop-blur-[20px] border-t border-[var(--divider)] pb-[var(--safe-bottom)]">
      <div className="flex justify-around items-center h-[var(--nav-height)] max-w-[480px] mx-auto">
        {tabs.map((tab) => {
          const active = location === tab.path;
          return (
            <button
              key={tab.label}
              onClick={() => navigate({ to: tab.path as "/" })}
              className={`flex flex-col items-center gap-1 px-4 py-2 transition-colors ${
                active ? "text-[var(--green)]" : "text-[var(--grey-dim)] hover:text-[var(--grey)]"
              }`}
            >
              <svg
                className="w-[22px] h-[22px] fill-none stroke-current"
                strokeWidth={active ? 2.2 : 1.8}
                strokeLinecap="round"
                strokeLinejoin="round"
                viewBox="0 0 24 24"
              >
                {tab.icon}
                {tab.iconExtra}
              </svg>
              <span className="font-[family-name:var(--font-ui)] text-[9px] font-bold tracking-[0.5px]">
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
