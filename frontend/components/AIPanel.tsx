"use client"

import { useEffect, useMemo, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import Image from "next/image"
import { fetchPrediction } from "@/lib/fetcher"
import { AIInsight } from "@/lib/types"
import { DRIVER_CODE_MAP, TEAM_MAP } from "@/lib/driverMeta"

type Props = {
  sessionId: number
  selectedDrivers: string[]
  simulationId: string | null
}

type DriverLogoProps = {
  driver: string
  className?: string
}

type SmoothImageProps = {
  src: string
  alt: string
  sizes: string
  className?: string
  wrapperClassName?: string
  loadedOpacityClass?: string
  onError?: () => void
}

const BUTTON_GRADIENT =
  "linear-gradient(135deg, #22d3ee 0%, #3b82f6 55%, #2563eb 100%)"

function SmoothImage({
  src,
  alt,
  sizes,
  className,
  wrapperClassName,
  loadedOpacityClass = "opacity-100",
  onError,
}: SmoothImageProps) {
  const [isLoaded, setIsLoaded] = useState(false)

  return (
    <div className={`relative h-full w-full ${wrapperClassName ?? ""}`}>
      <div
        className={`absolute inset-0 bg-gradient-to-br from-gray-800/70 via-gray-900/60 to-gray-950/80 transition-opacity duration-300 ${
          isLoaded ? "opacity-0" : "opacity-100"
        }`}
      />
      <Image
        src={src}
        alt={alt}
        fill
        sizes={sizes}
        className={`${className ?? ""} transition-[opacity,transform,filter] duration-300 ease-out ${
          isLoaded
            ? `${loadedOpacityClass} scale-100 blur-0`
            : "opacity-0 scale-[1.03] blur-sm"
        }`}
        onLoadingComplete={() => setIsLoaded(true)}
        onError={onError}
      />
    </div>
  )
}

function DriverLogo({ driver, className }: DriverLogoProps) {
  const driverCode = DRIVER_CODE_MAP[driver]
  const candidates = useMemo(
    () =>
      [
        `/driverLogos/${driver}.jpg`,
        `/driverLogos/${driver}.png`,
        driverCode ? `/driverLogos/${driverCode}.jpg` : null,
        driverCode ? `/driverLogos/${driverCode}.png` : null,
      ].filter((src): src is string => Boolean(src)),
    [driver, driverCode]
  )
  const [activeSrc, setActiveSrc] = useState(candidates[0])
  const [incomingSrc, setIncomingSrc] = useState<string | null>(null)
  const [isTransitioning, setIsTransitioning] = useState(false)

  useEffect(() => {
    let cancelled = false

    const loadImage = (src: string) =>
      new Promise<void>((resolve, reject) => {
        const img = new window.Image()
        img.onload = () => resolve()
        img.onerror = () => reject()
        img.src = src
      })

    const resolveBestLogo = async () => {
      let nextSrc = candidates[0]
      for (const src of candidates) {
        try {
          await loadImage(src)
          nextSrc = src
          break
        } catch {
          continue
        }
      }

      if (cancelled || nextSrc === activeSrc) {
        return
      }

      setIncomingSrc(nextSrc)
      setIsTransitioning(true)

      const timeoutId = setTimeout(() => {
        if (cancelled) {
          return
        }
        setActiveSrc(nextSrc)
        setIncomingSrc(null)
        setIsTransitioning(false)
      }, 280)

      return timeoutId
    }

    let timeoutId: ReturnType<typeof setTimeout> | null = null
    void resolveBestLogo().then((id) => {
      timeoutId = id ?? null
    })

    return () => {
      cancelled = true
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [activeSrc, candidates])

  return (
    <div className={`relative h-full w-full bg-black/20 ${className ?? ""}`}>
      <div
        className={`absolute inset-0 transition-opacity duration-300 ease-out ${
          isTransitioning ? "opacity-0" : "opacity-100"
        }`}
      >
        <SmoothImage
          key={`active-${activeSrc}`}
          src={activeSrc}
          alt={`Driver ${driver} logo`}
          sizes="(max-width: 768px) 20vw, 12vw"
          className="object-contain p-2"
        />
      </div>

      {incomingSrc && (
        <div
          className={`absolute inset-0 transition-opacity duration-300 ease-out ${
            isTransitioning ? "opacity-100" : "opacity-0"
          }`}
        >
          <SmoothImage
            key={`incoming-${incomingSrc}`}
            src={incomingSrc}
            alt={`Driver ${driver} logo`}
            sizes="(max-width: 768px) 20vw, 12vw"
            className="object-contain p-2"
          />
        </div>
      )}
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
  const leftCode = left ? DRIVER_CODE_MAP[left] ?? left : null
  const rightCode = right ? DRIVER_CODE_MAP[right] ?? right : null

  const formatPct = (value: number) => `${Math.round(value * 100)}%`
  const formatPitWindow = (driver: string) => {
    const pitWindow = result?.prediction.driver_pit_windows[driver]
    if (!pitWindow || pitWindow.length !== 2) {
      return "No clear pit window identified."
    }
    return `Pit window: Lap ${pitWindow[0]}-${pitWindow[1]}`
  }

  const getDriverReasoning = (driver: string) => {
    if (!result) {
      return []
    }

    const undercut = result.prediction.undercut_probability
    const overcut = result.prediction.overcut_probability
    const driverCode = DRIVER_CODE_MAP[driver] ?? driver
    const undercutActorCode = DRIVER_CODE_MAP[undercut.actor] ?? undercut.actor
    const overcutActorCode = DRIVER_CODE_MAP[overcut.actor] ?? overcut.actor

    return [
      formatPitWindow(driver),
      undercut.actor === driver
        ? `Undercut edge for ${driverCode}: ${formatPct(undercut.value)}`
        : `Undercut threat from ${undercutActorCode}: ${formatPct(undercut.value)}`,
      overcut.actor === driver
        ? `Overcut edge for ${driverCode}: ${formatPct(overcut.value)}`
        : `Overcut threat from ${overcutActorCode}: ${formatPct(overcut.value)}`,
    ]
  }

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg bg-gray-950 text-gray-200">
      <div className="relative h-[45%] px-4 pt-4">
        <div className="relative flex h-full items-stretch">
          <div className="relative flex flex-1 overflow-hidden rounded-l-md bg-gray-900">
            {left && (
              <>
                <DriverLogo
                  driver={left}
                  className="border-r border-white/10"
                />
                <SmoothImage
                  key={`left-portrait-${left}`}
                  src={`/portraits/${left}.png`}
                  alt={`Driver ${left}`}
                  sizes="(max-width: 768px) 20vw, 12vw"
                  className="object-contain object-right"
                  loadedOpacityClass="opacity-90"
                />
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
                <SmoothImage
                  key={`right-portrait-${right}`}
                  src={`/portraits/${right}.png`}
                  alt={`Driver ${right}`}
                  sizes="(max-width: 768px) 20vw, 12vw"
                  className="object-contain object-left"
                  loadedOpacityClass="opacity-90"
                />
                <DriverLogo
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
          <div className="space-y-6 text-sm">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-white/10 bg-gray-900/70 px-3 py-2">
                <div className="text-[11px] uppercase tracking-wide text-gray-400">Confidence</div>
                <div
                  className={`text-base font-semibold ${
                    result.confidence === "HIGH"
                      ? "text-green-400"
                      : result.confidence === "MEDIUM"
                      ? "text-yellow-400"
                      : "text-red-400"
                  }`}
                >
                  {result.confidence}
                </div>
              </div>

              <div className="rounded-md border border-cyan-400/25 bg-cyan-500/5 px-3 py-2">
                <div className="text-[11px] uppercase tracking-wide text-cyan-300/80">Undercut</div>
                <div className="text-base font-semibold text-cyan-200">
                  {(DRIVER_CODE_MAP[result.prediction.undercut_probability.actor] ??
                    result.prediction.undercut_probability.actor) +
                    ` · ${formatPct(result.prediction.undercut_probability.value)}`}
                </div>
              </div>

              <div className="rounded-md border border-blue-400/25 bg-blue-500/5 px-3 py-2">
                <div className="text-[11px] uppercase tracking-wide text-blue-300/80">Overcut</div>
                <div className="text-base font-semibold text-blue-200">
                  {(DRIVER_CODE_MAP[result.prediction.overcut_probability.actor] ??
                    result.prediction.overcut_probability.actor) +
                    ` · ${formatPct(result.prediction.overcut_probability.value)}`}
                </div>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {left && (
                <div className="rounded-md border border-white/10 bg-gray-900/60 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="text-base font-semibold text-gray-100">{leftCode}</div>
                    <div className="text-xs tracking-wide text-gray-400">{TEAM_MAP[left] ?? "Unknown Team"}</div>
                  </div>
                  <ul className="space-y-2 text-gray-300">
                    {getDriverReasoning(left).map((line, i) => (
                      <li key={`${left}-${i}`} className="rounded bg-gray-800/60 px-2.5 py-2 leading-relaxed">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {right && (
                <div className="rounded-md border border-white/10 bg-gray-900/60 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="text-base font-semibold text-gray-100">{rightCode}</div>
                    <div className="text-xs tracking-wide text-gray-400">{TEAM_MAP[right] ?? "Unknown Team"}</div>
                  </div>
                  <ul className="space-y-2 text-gray-300">
                    {getDriverReasoning(right).map((line, i) => (
                      <li key={`${right}-${i}`} className="rounded bg-gray-800/60 px-2.5 py-2 leading-relaxed">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="rounded-md border border-white/10 bg-gray-900/50 p-4">
              <div className="mb-3 text-sm font-semibold tracking-wide text-gray-200">General Reasoning</div>
              <ul className="space-y-2 text-gray-300">
                {result.reasoning.map((r, i) => (
                  <li key={i} className="rounded bg-gray-800/50 px-3 py-2 leading-relaxed">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
