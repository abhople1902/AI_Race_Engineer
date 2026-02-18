"use client"

import { useEffect, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import Image from "next/image"
import { fetchPrediction } from "@/lib/fetcher"
import { AIInsight } from "@/lib/types"
import { DRIVER_CODE_MAP } from "@/lib/driverMeta"

type Props = {
  sessionId: number
  selectedDrivers: string[]
  simulationId: string | null
}

type DriverLogoProps = {
  driver: string
  className?: string
}

const BUTTON_GRADIENT =
  "linear-gradient(135deg, #22d3ee 0%, #3b82f6 55%, #2563eb 100%)"

function DriverLogo({ driver, className }: DriverLogoProps) {
  const code = DRIVER_CODE_MAP[driver] ?? driver
  const candidates = [
    `/driverLogos/${code}.png`,
    `/driverLogos/${code}.jpg`,
    `/driverLogos/${driver}.png`,
    `/driverLogos/${driver}.jpg`,
  ]
  const [index, setIndex] = useState(0)
  const src = candidates[index]

  return (
    <div className={`relative h-full w-full bg-black/20 ${className ?? ""}`}>
      <Image
        src={src}
        alt={`${code} logo`}
        fill
        sizes="(max-width: 768px) 20vw, 12vw"
        className="object-contain p-2"
        onError={() => {
          setIndex((prev) => Math.min(prev + 1, candidates.length - 1))
        }}
      />
    </div>
  )
}

export default function AIPanel({
  sessionId,
  selectedDrivers,
  simulationId,
}: Props) {
  const mutation = useMutation({
    mutationFn: (driverNumbers: number[]) =>
      fetchPrediction(
        sessionId,
        driverNumbers,
        simulationId!
      ),
  })

  useEffect(() => {
    if (selectedDrivers.length < 2) {
      mutation.reset()
    }
  }, [selectedDrivers, mutation])

  const runPrediction = () => {
    if (selectedDrivers.length === 2 && simulationId) {
      mutation.mutate(selectedDrivers.map(Number))
    }
  }

  const left = selectedDrivers[0]
  const right = selectedDrivers[1]
  const result: AIInsight | null = mutation.data ?? null

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg bg-gray-950 text-gray-200">
      <div className="relative h-[45%] px-4 pt-4">
        <div className="relative flex h-full items-stretch">
          <div className="relative flex flex-1 overflow-hidden rounded-l-md bg-gray-900">
            {left && (
              <>
                <DriverLogo
                  key={`left-logo-${left}`}
                  driver={left}
                  className="border-r border-white/10"
                />
                <div className="relative h-full w-full">
                  <Image
                    src={`/portraits/${left}.jpg`}
                    alt={`Driver ${left}`}
                    fill
                    sizes="(max-width: 768px) 20vw, 12vw"
                    className="object-contain object-right opacity-90"
                  />
                </div>
              </>
            )}
            {!left && (
              <div className="absolute inset-0 flex items-center justify-center text-xs tracking-wider text-gray-500">
                SELECT DRIVER
              </div>
            )}
          </div>

          <div className="relative flex flex-1 overflow-hidden rounded-r-md bg-gray-900">
            {right && (
              <>
                <div className="relative h-full w-full">
                  <Image
                    src={`/portraits/${right}.jpg`}
                    alt={`Driver ${right}`}
                    fill
                    sizes="(max-width: 768px) 20vw, 12vw"
                    className="object-contain object-left opacity-90"
                  />
                </div>
                <DriverLogo
                  key={`right-logo-${right}`}
                  driver={right}
                  className="border-l border-white/10"
                />
              </>
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
          disabled={
            !simulationId ||
            selectedDrivers.length < 2 ||
            mutation.isPending
          }
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
