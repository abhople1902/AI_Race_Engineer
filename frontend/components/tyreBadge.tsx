import { TyreCompound } from "@/lib/types"

const COLOR_MAP: Record<TyreCompound, string> = {
  SOFT: "bg-red-500 text-white",
  MEDIUM: "bg-yellow-400 text-black",
  HARD: "bg-gray-300 text-black",
  INTERMEDIATE: "bg-green-500 text-white",
  WET: "bg-blue-500 text-white",
  UNKNOWN: "bg-gray-200 text-gray-600",
}

export default function TyreBadge({ compound }: { compound: TyreCompound }) {
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-semibold ${COLOR_MAP[compound]}`}
    >
      {compound}
    </span>
  )
}
