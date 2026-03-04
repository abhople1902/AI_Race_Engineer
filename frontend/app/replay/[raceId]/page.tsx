"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import Image from "next/image"

import AIPanel from "@/components/AIPanel"
import LeaderboardTable from "@/components/LeaderboardTable"
import RaceControlDrawer from "@/components/RaceControlDrawer"
import {
  endReplaySession,
  fetchLeaderboard,
  fetchReplayStatus,
  startReplaySession,
} from "@/lib/fetcher"
import { getReplaySessionById } from "@/lib/replaySessions"
import { DRIVER_CODE_MAP } from "@/lib/driverMeta"

const STICKER_POSITIONS = [
  "top-[-40px] left-[12%] rotate-[-10deg]",
  "top-[-34px] right-[10%] rotate-[9deg]",
  "top-[22%] left-[-34px] rotate-[-8deg]",
  "top-[28%] right-[-36px] rotate-[11deg]",
]

export default function ReplayPage() {
  const params = useParams<{ raceId: string }>()
  const router = useRouter()
  const raceId = params.raceId

  const session = useMemo(
    () => getReplaySessionById(raceId),
    [raceId]
  )

  const [selectedDrivers, setSelectedDrivers] =
    useState<string[]>([])
  const [raceControlOpen, setRaceControlOpen] = useState(false)
  const [isStartingReplay, setIsStartingReplay] = useState(false)
  const [isEndingReplay, setIsEndingReplay] = useState(false)
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

  const { data: replayStatusData } = useQuery({
    queryKey: ["replay-status", session?.sessionKey, simulationId],
    queryFn: () =>
      fetchReplayStatus(
        session!.sessionKey,
        simulationId!
      ),
    refetchInterval: 5000,
    enabled: Boolean(session && simulationId),
  })

  const replayEnded =
    replayStatusData?.status === "COMPLETED" ||
    replayStatusData?.status === "STOPPED" ||
    replayStatusData?.status === "FAILED"

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

  const handleEndReplay = async () => {
    if (!simulationId) {
      return
    }

    setIsEndingReplay(true)
    try {
      await endReplaySession(simulationId)
      router.push("/")
    } catch {
      setStartError("Failed to end replay session")
    } finally {
      setIsEndingReplay(false)
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
                replayEnded={replayEnded}
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

      {hasReplayStarted && (
        <button
          onClick={handleEndReplay}
          disabled={isEndingReplay}
          className="absolute right-6 top-6 z-40 rounded-md border border-red-400/50 bg-red-500/20 px-4 py-2 text-sm font-medium text-red-200 transition hover:bg-red-500/30 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isEndingReplay ? "Ending..." : "End Replay"}
        </button>
      )}

      {!hasReplayStarted && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-950/35 px-6 py-8">
          <div className="relative max-h-[calc(100vh-4rem)] w-full max-w-3xl overflow-visible rounded-2xl border border-slate-700 bg-slate-900/95 shadow-2xl">
            <Link
              href="/"
              className="absolute top-4 left-4 z-30 rounded-md border border-white/20 bg-slate-950/70 px-3 py-1.5 text-xs font-medium tracking-wide text-slate-200 transition hover:bg-slate-900"
            >
              Back
            </Link>

            <div className="relative h-[34vh] min-h-[220px] max-h-[320px] w-full">
              <Image
                src={session.heroImage}
                alt={`${session.name} cover`}
                fill
                priority
                className="rounded-t-2xl object-cover object-center"
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-36 bg-gradient-to-b from-transparent via-slate-900/70 to-slate-900" />

              {session.stickers.map((stickerSrc, idx) => (
                <div
                  key={stickerSrc}
                  className={`pointer-events-none absolute z-40 h-28 w-28 overflow-hidden rounded-xl border-2 border-white/60 bg-slate-800 shadow-[0_16px_28px_rgba(0,0,0,0.45)] ring-1 ring-black/25 sm:h-32 sm:w-32 ${STICKER_POSITIONS[idx] ?? ""}`}
                >
                  <Image
                    src={stickerSrc}
                    alt={`race sticker ${idx + 1}`}
                    fill
                    className="object-cover saturate-110"
                  />
                </div>
              ))}
            </div>

            <div className="space-y-6 px-6 pb-6 pt-2 sm:px-8">
              <section>
                <div className="text-center text-[11px] uppercase tracking-[0.28em] text-amber-300/90">
                  Podium Finishes
                </div>
                <div className="mt-3 grid grid-cols-3 items-end gap-3">
                  {[
                    { driverNumber: session.podium[1], finish: 2 },
                    { driverNumber: session.podium[0], finish: 1 },
                    { driverNumber: session.podium[2], finish: 3 },
                  ].map(({ driverNumber, finish }) => {
                    const code = DRIVER_CODE_MAP[driverNumber] ?? driverNumber
                    const isWinner = finish === 1
                    return (
                      <div
                        key={`${driverNumber}-${finish}`}
                        className={`rounded-xl border px-3 py-3 text-center ${
                          isWinner
                            ? "border-amber-300/60 bg-amber-300/10"
                            : "border-slate-700 bg-slate-800/70"
                        }`}
                      >
                        <div
                          className={`relative mx-auto overflow-hidden rounded-lg ${
                            isWinner ? "h-20 w-20 sm:h-24 sm:w-24" : "h-16 w-16 sm:h-20 sm:w-20"
                          }`}
                        >
                          <Image
                            src={`/portraits/${driverNumber}.png`}
                            alt={`Driver ${driverNumber}`}
                            fill
                            className="object-contain"
                          />
                        </div>
                        <div className="mt-2 text-[10px] uppercase tracking-[0.2em] text-slate-400">
                          {finish}
                          {finish === 1 ? "st" : finish === 2 ? "nd" : "rd"}
                        </div>
                        <div className="text-sm font-semibold text-white">{code}</div>
                      </div>
                    )
                  })}
                </div>
              </section>

              <div className="text-center">
                <div className="text-xs uppercase tracking-[0.18em] text-sky-300/90">
                  {session.name}
                </div>
                <h1 className="mt-2 text-2xl font-semibold text-white">
                  Start Replay
                </h1>
                <p className="mt-2 text-sm text-slate-300">
                  As soon as you start, the session replay will begin.
                </p>
              </div>

              {startError && (
                <p className="text-center text-sm text-red-400">{startError}</p>
              )}

              <button
                onClick={handleStartReplay}
                disabled={isStartingReplay}
                className="w-full rounded-lg bg-sky-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isStartingReplay ? "Starting..." : "Start Replay"}
              </button>

              <div className="text-center">
                <Link
                  href="/"
                  className="text-sm text-slate-400 hover:text-slate-300"
                >
                  Back to race selection
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
