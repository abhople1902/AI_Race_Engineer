import { NextResponse } from "next/server"

const REDIS_WRITER_BASE_URL =
  process.env.REDIS_WRITER_BASE_URL ?? "http://localhost:8001"

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

  const upstreamUrl = new URL(`${REDIS_WRITER_BASE_URL}/replay-status`)
  upstreamUrl.searchParams.set("session_key", sessionKey)
  upstreamUrl.searchParams.set("simulation_id", simulationId)

  try {
    const res = await fetch(upstreamUrl.toString(), { method: "GET" })
    const data = await res.json()

    if (!res.ok) {
      return NextResponse.json(
        { error: data?.error ?? "Replay status request failed" },
        { status: res.status }
      )
    }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "Replay status request failed" },
      { status: 500 }
    )
  }
}
