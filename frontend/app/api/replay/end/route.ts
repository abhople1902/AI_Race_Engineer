import { NextResponse } from "next/server"

const REDIS_WRITER_BASE_URL =
  process.env.REDIS_WRITER_BASE_URL ?? "http://localhost:8001"

export async function POST(req: Request) {
  const body = await req.json()

  try {
    const res = await fetch(`${REDIS_WRITER_BASE_URL}/end-replay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    const data = await res.json()

    if (!res.ok) {
      return NextResponse.json(
        { error: data?.error ?? "Replay end failed" },
        { status: res.status }
      )
    }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "Replay end request failed" },
      { status: 500 }
    )
  }
}
