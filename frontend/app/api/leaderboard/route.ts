import { NextResponse } from "next/server"
import redis from "@/lib/redis"
import { DRIVER_CODE_MAP, TEAM_MAP } from "@/lib/driverMeta"
import { LeaderboardEntry, LeaderboardResponse, TyreCompound } from "@/lib/types"

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const sessionKey = searchParams.get("session_key")
  const simulationId = searchParams.get("simulation_id")

  if (!sessionKey || !simulationId) {
    return NextResponse.json(
      { error: "session_key and simulation_id are required" },
      { status: 400 }
    )
  }

  const prefix = `sim:${simulationId}:session:${sessionKey}`

  // 1. Read session meta
  const metaKey = `${prefix}:meta`
  const meta = await redis.hgetall(metaKey)

  const timestamp = meta.last_event_ts ?? new Date().toISOString()

  // 2. Read leaderboard ordering
  const leaderboardKey = `${prefix}:leaderboard`
  const zset = await redis.zrange(leaderboardKey, 0, -1, "WITHSCORES")

  // zset = [driver, pos, driver, pos, ...]
  const orderedDrivers: { driver: string; position: number }[] = []

  for (let i = 0; i < zset.length; i += 2) {
    orderedDrivers.push({
      driver: zset[i],
      position: Number(zset[i + 1]),
    })
  }

  const leaderboard: LeaderboardEntry[] = []

  let prevGap = 0

  // 3. Build leaderboard entries
  for (const { driver, position } of orderedDrivers) {
    const driverKey = `${prefix}:driver:${driver}`
    const data = await redis.hgetall(driverKey)

    if (!data || data.status !== "RUNNING") {
      continue
    }

    const gap = Number(data.gap_to_leader)

    const stintKey = `${prefix}:driver:${driver}:stint`
    const stint = await redis.hgetall(stintKey)

    const rawCompound = stint?.compound?.toUpperCase()
    const validCompounds: TyreCompound[] = [
      "SOFT",
      "MEDIUM",
      "HARD",
      "INTERMEDIATE",
      "WET",
      "UNKNOWN",
    ]
    const tyreCompound: TyreCompound =
      (rawCompound && validCompounds.includes(rawCompound as TyreCompound)
        ? (rawCompound as TyreCompound)
        : "UNKNOWN")

    const interval =
      position === 1 ? 0 : Number((gap - prevGap).toFixed(3))

    prevGap = gap

    leaderboard.push({
      position,
      driver_number: driver,
      driver_code: DRIVER_CODE_MAP[driver] ?? driver,
      team: TEAM_MAP[driver] ?? "Unknown",
      gap_to_leader: gap,
      interval,
      tyre_compound: tyreCompound
    })
  }

  const response: LeaderboardResponse = {
    session_key: sessionKey,
    timestamp,
    leaderboard,
  }

  return NextResponse.json(response)
}
