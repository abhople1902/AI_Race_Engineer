"use client"

import { useEffect } from "react"
import { useMutation } from "@tanstack/react-query"
import Image from "next/image"
import { fetchPrediction } from "@/lib/fetcher"
import { AIInsight } from "@/lib/types"
import { DRIVER_GRADIENTS, DEFAULT_GRADIENT } from "@/lib/teamGradients"
import { TEAM_MAP } from "@/lib/driverMeta"

type Props = {
  sessionId: number
  selectedDrivers: string[]
}

const BUTTON_GRADIENT =
  "linear-gradient(135deg, #22d3ee 0%, #3b82f6 55%, #2563eb 100%)"

export default function AIPanel({
  sessionId,
  selectedDrivers,
}: Props) {
  const mutation = useMutation({
    mutationFn: (driverNumbers: number[]) =>
      fetchPrediction(sessionId, driverNumbers),
  })

  useEffect(() => {
    if (selectedDrivers.length < 2) {
      mutation.reset()
    }
  }, [selectedDrivers, mutation])

  const runPrediction = () => {
    if (selectedDrivers.length === 2) {
      mutation.mutate(selectedDrivers.map(Number))
    }
  }

  const left = selectedDrivers[0]
  const right = selectedDrivers[1]
  const result: AIInsight | null = mutation.data ?? null
  const leftTeam = left ? TEAM_MAP[left] : undefined
  const rightTeam = right ? TEAM_MAP[right] : undefined
  const leftGradient = left
    ? DRIVER_GRADIENTS[leftTeam ?? ""] ?? DEFAULT_GRADIENT
    : DEFAULT_GRADIENT
  const rightGradientBase = right
    ? DRIVER_GRADIENTS[rightTeam ?? ""] ?? DEFAULT_GRADIENT
    : DEFAULT_GRADIENT
  const rightGradient = rightGradientBase.replace("to right", "to left")
  const darkOverlay = "linear-gradient(rgba(0, 0, 0, 0.38), rgba(0, 0, 0, 0.38))"

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg bg-gray-950 text-gray-200">
      <div className="relative h-[45%] px-4 pt-4">
        <div className="relative flex h-full items-stretch">
          <div
            className="relative flex-1 overflow-hidden rounded-l-md"
            style={{
              background: `${darkOverlay}, ${leftGradient}`,
            }}
          >
            {left && (
              <Image
                src={`/portraits/${left}.jpg`}
                alt={`Driver ${left}`}
                fill
                className="object-contain object-right opacity-85"
              />
            )}
            {!left && (
              <div className="absolute inset-0 flex items-center justify-center text-xs tracking-wider text-gray-500">
                SELECT DRIVER
              </div>
            )}
          </div>

          <div
            className="relative flex-1 overflow-hidden rounded-r-md"
            style={{
              background: `${darkOverlay}, ${rightGradient}`,
            }}
          >
            {right && (
              <Image
                src={`/portraits/${right}.jpg`}
                alt={`Driver ${right}`}
                fill
                className="object-contain object-left opacity-85"
              />
            )}
            {!right && (
              <div className="absolute inset-0 flex items-center justify-center text-xs tracking-wider text-gray-500">
                SELECT DRIVER
              </div>
            )}
          </div>
        </div>

        <button
          onClick={runPrediction}
          disabled={selectedDrivers.length < 2 || mutation.isPending}
          className="absolute left-1/2 bottom-[-28px] z-20 h-16 w-16 -translate-x-1/2 rounded-full border border-white/35 shadow-xl transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50"
          style={{ background: BUTTON_GRADIENT }}
          title="Run Strategy Analysis"
          aria-label="Run Strategy Analysis"
        >
          <Image
            src="/ai-analysis.svg"
            alt="AI analysis"
            className="mx-auto h-8 w-8"
            width={32}
            height={32}
          />
        </button>
      </div>

      <div className="flex-1 overflow-auto px-6 pb-6 pt-10">
        {mutation.isPending && (
          <div className="text-gray-400">
            Running model...
          </div>
        )}

        {result && (
          <div className="space-y-5 text-sm">
            <div className="text-lg font-semibold">
              Confidence:{" "}
              <span
                className={
                  result.confidence === "HIGH"
                    ? "text-green-400"
                    : result.confidence === "MEDIUM"
                    ? "text-yellow-400"
                    : "text-red-400"
                }
              >
                {result.confidence}
              </span>
            </div>

            <div>
              <strong>Undercut:</strong>{" "}
              {result.prediction.undercut_probability.actor} (
              {result.prediction.undercut_probability.value})
            </div>

            <div>
              <strong>Overcut:</strong>{" "}
              {result.prediction.overcut_probability.actor} (
              {result.prediction.overcut_probability.value})
            </div>

            <div>
              <strong>Reasoning:</strong>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-gray-300">
                {result.reasoning.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
