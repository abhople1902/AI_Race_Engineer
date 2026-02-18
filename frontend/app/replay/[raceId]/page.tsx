"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"

import AIPanel from "@/components/AIPanel"
import LeaderboardTable from "@/components/LeaderboardTable"
import RaceControlDrawer from "@/components/RaceControlDrawer"
import {
  fetchLeaderboard,
  startReplaySession,
} from "@/lib/fetcher"
import { getReplaySessionById } from "@/lib/replaySessions"

export default function ReplayPage() {
  const params = useParams<{ raceId: string }>()
  const raceId = params.raceId

  const session = useMemo(
    () => getReplaySessionById(raceId),
    [raceId]
  )

  const [selectedDrivers, setSelectedDrivers] =
    useState<string[]>([])
  const [raceControlOpen, setRaceControlOpen] = useState(false)
  const [isStartingReplay, setIsStartingReplay] = useState(false)
  const [simulationId, setSimulationId] = useState<string | null>(null)
  const [startError, setStartError] = useState<string | null>(null)

  const hasReplayStarted = simulationId !== null

  const { data, isLoading, isError } = useQuery({
    queryKey: ["leaderboard", session?.sessionKey, simulationId],
    queryFn: () =>
      fetchLeaderboard(
        session!.sessionKey,
        simulationId!
      ),
    refetchInterval: 3000,
    enabled: Boolean(session && simulationId),
  })

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

  const handleStartReplay = async () => {
    if (!session) {
      return
    }

    setStartError(null)
    setIsStartingReplay(true)

    try {
      const { simulation_id } = await startReplaySession({
        sessionKey: Number(session.sessionKey),
        startTime: session.startTime,
      })
      setSimulationId(simulation_id)
    } catch {
      setStartError("Failed to start replay session")
    } finally {
      setIsStartingReplay(false)
    }
  }

  if (!session) {
    return (
      <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
        <p className="text-red-400">Replay session not found.</p>
        <Link
          href="/"
          className="mt-4 inline-block text-sky-300 hover:text-sky-200"
        >
          Back to sessions
        </Link>
      </main>
    )
  }

  return (
    <main className="relative h-screen overflow-hidden bg-slate-950 p-4 text-slate-100">
      <div
        className={`h-full transition ${
          hasReplayStarted ? "blur-0" : "pointer-events-none blur-sm"
        }`}
      >
        {!hasReplayStarted && (
          <div className="flex h-full items-center justify-center text-slate-400">
            Replay has not started yet.
          </div>
        )}

        {hasReplayStarted && isLoading && (
          <div className="flex h-full items-center justify-center text-slate-300">
            Loading replay data...
          </div>
        )}

        {hasReplayStarted && isError && (
          <div className="flex h-full items-center justify-center text-red-400">
            Failed to load replay data.
          </div>
        )}

        {hasReplayStarted && data && (
          <div className="grid h-full grid-cols-[40%_60%] gap-4 overflow-hidden">
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
                  sessionId={Number(session.sessionKey)}
                  selectedDrivers={selectedDrivers}
                  simulationId={simulationId}
                />
              </div>

              <RaceControlDrawer
                sessionKey={session.sessionKey}
                simulationId={simulationId}
                isOpen={raceControlOpen}
                onToggle={() =>
                  setRaceControlOpen((prev) => !prev)
                }
              />
            </div>
          </div>
        )}
      </div>

      {!hasReplayStarted && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-950/35 p-6">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900/95 p-8 text-center shadow-2xl">
            <div className="text-xs uppercase tracking-[0.18em] text-sky-300/90">
              {session.name}
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-white">
              Start Replay
            </h1>
            <p className="mt-2 text-sm text-slate-300">
              As soon as you start, the session replay will begin.
            </p>

            {startError && (
              <p className="mt-4 text-sm text-red-400">{startError}</p>
            )}

            <button
              onClick={handleStartReplay}
              disabled={isStartingReplay}
              className="mt-6 w-full rounded-lg bg-sky-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isStartingReplay ? "Starting..." : "Start Replay"}
            </button>

            <Link
              href="/"
              className="mt-4 inline-block text-sm text-slate-400 hover:text-slate-300"
            >
              Back to race selection
            </Link>
          </div>
        </div>
      )}
    </main>
  )
}
