"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { fetchPrediction } from "@/lib/fetcher"
import { AIInsight } from "@/lib/types"

type Props = {
  sessionId: number
  availableDrivers: string[]
}

export default function AIPanel({
  sessionId,
  availableDrivers,
}: Props) {
  const [selected, setSelected] = useState<string[]>([])
  const [result, setResult] = useState<AIInsight | null>(null)

  const mutation = useMutation({
    mutationFn: (drivers: number[]) =>
      fetchPrediction(sessionId, drivers),
    onSuccess: (data) => setResult(data),
  })

  const toggleDriver = (driver: string) => {
    if (selected.includes(driver)) {
      setSelected(selected.filter((d) => d !== driver))
    } else {
      setSelected([...selected, driver])
    }
  }

  const runPrediction = () => {
    if (selected.length >= 2) {
      mutation.mutate(selected.map(Number))
    }
  }

  return (
    <div className="h-full flex flex-col p-4">
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">
          Select Drivers
        </div>
        <div className="flex flex-wrap gap-2">
          {availableDrivers.map((d) => (
            <button
              key={d}
              onClick={() => toggleDriver(d)}
              className={`px-2 py-1 rounded text-xs border ${
                selected.includes(d)
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-300"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={runPrediction}
        disabled={selected.length < 2 || mutation.isPending}
        className="mb-4 bg-blue-600 text-white px-3 py-2 rounded disabled:opacity-50"
      >
        Run Strategy Analysis
      </button>

      <div className="flex-1 overflow-auto text-sm text-gray-300">
        {mutation.isPending && <div>Running model…</div>}

        {result && (
          <div className="space-y-3">
            <div>
              <strong>Confidence:</strong> {result.confidence}
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
              <ul className="list-disc pl-4">
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
