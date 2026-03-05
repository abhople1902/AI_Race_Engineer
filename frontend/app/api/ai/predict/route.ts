import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const body = await req.json()

  try {
    const res = await fetch(`${process.env.AI_SERVICE_URL}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      throw new Error("AI service failed")
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "AI request failed" },
      { status: 500 }
    )
  }
}
