import { NextResponse } from "next/server"
import redis from "@/lib/redis"

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const sessionKey = searchParams.get("session_key")

  if (!sessionKey) {
    return NextResponse.json(
      { error: "session_key required" },
      { status: 400 }
    )
  }

  const key = `session:${sessionKey}:race_control`

  const messages = await redis.lrange(key, 0, 49)

  const parsed = messages.map((m) => JSON.parse(m))

  return NextResponse.json(parsed)
}
