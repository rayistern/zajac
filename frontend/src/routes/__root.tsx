import { createRootRoute, Outlet } from "@tanstack/react-router";
import { AudioPlayerProvider } from "../hooks/useAudioPlayer";
import { MiniPlayer } from "../components/layout/MiniPlayer";
import { BottomNav } from "../components/layout/BottomNav";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <AudioPlayerProvider>
      <div className="min-h-screen bg-[var(--bg)] text-white pb-[calc(var(--nav-height)+var(--safe-bottom)+80px)]" role="application" lang="en">
        <Outlet />
        <MiniPlayer />
        <BottomNav />
      </div>
    </AudioPlayerProvider>
  );
}
