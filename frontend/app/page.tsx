"use client"

import { useQuery } from "@tanstack/react-query"
import LeaderboardTable from "@/components/LeaderboardTable"
import { fetchLeaderboard } from "@/lib/fetcher"

const SESSION_KEY = "9869" // temp

export default function Home() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["leaderboard", SESSION_KEY],
    queryFn: () => fetchLeaderboard(SESSION_KEY),
    refetchInterval: 3000,
  })

  if (isLoading) {
    return <div className="p-6">Loading leaderboard…</div>
  }

  if (isError || !data) {
    return (
      <div className="p-6 text-red-600">
        Failed to load leaderboard
      </div>
    )
  }

  return (
    <main className="p-6">
      <h1 className="text-xl font-semibold mb-4">
        Live Leaderboard
      </h1>

      <LeaderboardTable data={data.leaderboard} />
    </main>
  )
}
