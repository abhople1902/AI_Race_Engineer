"use client"

import { useQuery } from "@tanstack/react-query"
import LeaderboardTable from "@/components/LeaderboardTable"
import { fetchLeaderboard } from "@/lib/fetcher"
import AIPanel from "@/components/AIPanel"

const SESSION_KEY = "9869"

export default function Home() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["leaderboard", SESSION_KEY],
    queryFn: () => fetchLeaderboard(SESSION_KEY),
    refetchInterval: 3000,
  })

  if (isLoading) {
    return <div className="p-6">Loading…</div>
  }

  if (isError || !data) {
    return <div className="p-6 text-red-600">Error loading data</div>
  }

  return (
    <div className="h-screen grid grid-cols-[40%_60%] gap-4 p-4">
      {/* LEFT: LEADERBOARD (FULL HEIGHT) */}
      <div className="h-full">
        <LeaderboardTable data={data.leaderboard} />
      </div>

      {/* RIGHT: AI + RACE CONTROL */}
      <div className="h-full grid grid-rows-[70%_30%] gap-4">
        {/* AI PANEL */}
        <div className="rounded-lg border border-dashed border-gray-700 flex items-center justify-center text-gray-500">
          <AIPanel
            sessionId={9869}
            availableDrivers={data.leaderboard.map(d => d.driver_number)}
          />

        </div>

        { }
        <div className="rounded-lg border border-gray-800 bg-gray-950 text-sm text-gray-400 flex items-center justify-center">
          Race control messages (Kafka later)
        </div>
      </div>
    </div>
  )
}