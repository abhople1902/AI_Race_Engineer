"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchRaceControl } from "@/lib/fetcher"
import { RaceControlMessage } from "@/lib/types"
import { useEffect, useRef, useMemo } from "react"

type Props = {
  sessionKey: string
  simulationId: string | null
  isOpen: boolean
  onToggle: () => void
}

export default function RaceControlDrawer({
  sessionKey,
  simulationId,
  isOpen,
  onToggle,
}: Props) {
  const { data } = useQuery({
    queryKey: ["race-control", sessionKey, simulationId],
    queryFn: () =>
      fetchRaceControl(
        sessionKey,
        simulationId!
      ),
    refetchInterval: 3000,
    enabled: Boolean(simulationId),
  })

  const containerRef = useRef<HTMLDivElement>(null)
  const lastSafetyCarRef = useRef<string | null>(null)

  // Auto-scroll
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = 0
    }
  }, [data])

  useEffect(() => {
    if (!data || data.length === 0) return
    const newest = data[0]

    // Safety car sound (only once per new SC event)
    if (
      newest.category === "SafetyCar" &&
      newest.date !== lastSafetyCarRef.current
    ) {
      lastSafetyCarRef.current = newest.date
      const audio = new Audio("/sounds/safetycar.mp3")
      audio.play().catch(() => {})
    }
  }, [data])

  const activeBlinkId = useMemo(() => {
    if (!data || data.length === 0) {
      return null
    }

    const newest = data[0]
    const isCritical =
      newest.flag === "DOUBLE YELLOW" ||
      newest.category === "SafetyCar" ||
      newest.message.includes("VIRTUAL SAFETY CAR")

    return isCritical ? newest.date : null
  }, [data])

  // Collapse repeated CLEAR
  const filteredMessages = useMemo(() => {
    if (!data) return []

    const result: RaceControlMessage[] = []
    let lastMessage: string | null = null

    for (const msg of data) {
      if (
        msg.flag === "CLEAR" &&
        msg.message === lastMessage
      ) {
        continue
      }

      result.push(msg)
      lastMessage = msg.message
    }

    return result
  }, [data])

  const getStyle = (msg: RaceControlMessage) => {
    if (msg.flag === "DOUBLE YELLOW")
      return "bg-yellow-500/10 border-yellow-500 text-yellow-400"
    if (msg.flag === "GREEN")
      return "bg-green-500/10 border-green-500 text-green-400"
    if (msg.category === "SafetyCar")
      return "bg-orange-500/10 border-orange-500 text-orange-400"
    if (msg.category === "SessionStatus")
      return "bg-blue-500/10 border-blue-500 text-blue-400"
    return "bg-gray-800 border-gray-700 text-gray-300"
  }

  const getBlinkClass = (msg: RaceControlMessage) => {
    if (msg.date !== activeBlinkId) return ""

    // Faster blink for SC / VSC
    if (
      msg.category === "SafetyCar" ||
      msg.message.includes("VIRTUAL SAFETY CAR")
    ) {
      return "animate-[pulse_0.6s_ease-in-out_infinite]"
    }

    // Slightly slower for DOUBLE YELLOW
    if (msg.flag === "DOUBLE YELLOW") {
      return "animate-[pulse_1s_ease-in-out_infinite]"
    }

    return ""
  }

  return (
    <div
      className={`absolute bottom-0 left-0 right-0 z-30 rounded-t-lg border-t border-gray-800 bg-gray-950 transition-transform duration-300 ${
        isOpen ? "translate-y-0" : "translate-y-[calc(100%-2rem)]"
      }`}
      style={{ height: "30vh" }}
    >
      {/* Toggle Bar */}
      <div
        className="flex items-center justify-center py-2 cursor-pointer text-gray-400 text-sm tracking-wide"
        onClick={onToggle}
      >
        {isOpen ? "↓ Hide Race Control" : "↑ Race Control"}
      </div>

      {/* Messages */}
      <div
        ref={containerRef}
        className="h-[85%] overflow-auto px-4 pb-4 space-y-3 text-sm"
      >
        {filteredMessages.map((msg, idx) => (
          <div
            key={msg.date + idx}
            className={`border-l-4 px-3 py-2 rounded-md transition-all duration-300 ${getStyle(
              msg
            )} ${getBlinkClass(msg)}`}
          >
            <div className="flex justify-between text-xs opacity-70 mb-1">
              <div className="flex items-center gap-2">
                <span>L{msg.lap_number ?? "-"}</span>

                {msg.driver_number && (
                  <span className="px-2 py-[2px] rounded bg-gray-700 text-gray-200 text-[10px]">
                    #{msg.driver_number}
                  </span>
                )}

                {msg.category === "SafetyCar" && (
                  <span className="px-2 py-[2px] rounded-full bg-orange-500 text-black text-[10px] font-bold">
                    SC
                  </span>
                )}

                {msg.message.includes("VIRTUAL SAFETY CAR") && (
                  <span className="px-2 py-[2px] rounded-full bg-orange-400 text-black text-[10px] font-bold">
                    VSC
                  </span>
                )}
              </div>

              <span>
                {new Date(msg.date).toLocaleTimeString()}
              </span>
            </div>

            <div className="font-medium">
              {msg.message}
            </div>

            {msg.sector && (
              <div className="text-xs opacity-60 mt-1">
                Sector {msg.sector}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
