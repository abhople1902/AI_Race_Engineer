"use client"

import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import LeaderboardTable from "@/components/LeaderboardTable"
import { fetchLeaderboard } from "@/lib/fetcher"
import AIPanel from "@/components/AIPanel"
import RaceControlDrawer from "@/components/RaceControlDrawer"

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
    <div className="grid h-screen grid-cols-[40%_60%] gap-4 overflow-hidden p-4">
      <div className="h-full">
        <LeaderboardTable
          data={data.leaderboard}
          selectedDrivers={selectedDrivers}
          onToggleDriver={toggleDriver}
        />
      </div>

      <div className="relative h-full overflow-hidden">
        <div className="h-full rounded-lg border border-gray-700">
          <AIPanel
            sessionId={9869}
            selectedDrivers={selectedDrivers}
          />
        </div>

        <RaceControlDrawer
          sessionKey={SESSION_KEY}
          isOpen={raceControlOpen}
          onToggle={() => setRaceControlOpen((prev) => !prev)}
        />
      </div>
    </div>
  )
}
