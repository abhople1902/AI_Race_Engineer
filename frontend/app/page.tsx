"use client"

import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
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

  const [selectedDrivers, setSelectedDrivers] =
    useState<string[]>([])

  const [raceControlOpen, setRaceControlOpen] = useState(false)

  const toggleDriver = (driver: string) => {
    setSelectedDrivers((prev) => {
      if (prev.includes(driver)) {
        return prev.filter((d) => d !== driver)
      }

      if (prev.length >= 2) {
        return [prev[1], driver]
      }

      return [...prev, driver]
    })
  }

  if (isLoading) {
    return <div className="p-6">Loading…</div>
  }

  if (isError || !data) {
    return <div className="p-6 text-red-600">Error</div>
  }

  return (
    <div className="h-screen grid grid-cols-[40%_60%] gap-4 p-4">
      {/* Leaderboard */}
      <div className="h-full">
        <LeaderboardTable
          data={data.leaderboard}
          selectedDrivers={selectedDrivers}
          onToggleDriver={toggleDriver}
        />
      </div>

      {/* AI + Race Control */}
      <div className="relative h-full">
        <div className="h-full rounded-lg border border-gray-700">
          <AIPanel
            sessionId={9869}
            selectedDrivers={selectedDrivers}
          />
        </div>

        <div
          className={`absolute bottom-0 left-0 right-0 bg-gray-950 border-t border-gray-800 transition-transform duration-300 ${raceControlOpen
              ? "translate-y-0"
              : "translate-y-[85%]"
            }`}
          style={{ height: "30vh" }}
        >
          <div
            className="flex items-center justify-center py-2 cursor-pointer text-gray-400 text-sm"
            onClick={() => setRaceControlOpen(!raceControlOpen)}
          >
            ↑ Race Control
          </div>

          <div className="p-4 text-gray-400 text-sm">
            Race control messages (Kafka later)
          </div>
        </div>
      </div>
    </div>
  )
}
