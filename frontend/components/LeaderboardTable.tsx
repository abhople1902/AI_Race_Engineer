import { LeaderboardEntry } from "@/lib/types"
import TyreBadge from "./tyreBadge"
import {
  DRIVER_GRADIENTS,
  TEAM_GRADIENTS,
  DEFAULT_GRADIENT,
} from "@/lib/teamGradients"

type Props = {
  data: LeaderboardEntry[]
  selectedDrivers: string[]
  onToggleDriver: (driver: string) => void
}

const MAX_DRIVERS = 20
const HEADER_HEIGHT_REM = 2.5

export default function LeaderboardTable({
  data,
  selectedDrivers,
  onToggleDriver,
}: Props) {
  const rowHeightClass = `h-[calc((100%-${HEADER_HEIGHT_REM}rem)/${MAX_DRIVERS})]`

  return (
    <div className="h-full rounded-lg border border-gray-800 bg-gray-950">
      <table className="h-full w-full table-fixed text-sm text-gray-100">
        <thead className="bg-gray-900 text-gray-300">
          <tr className="h-10">
            <th className="px-3 py-1 text-left">Pos</th>
            <th className="px-3 py-1 text-left">Driver</th>
            <th className="px-3 py-1 text-left">Team</th>
            <th className="px-3 py-1 text-right">Gap</th>
            <th className="px-3 py-1 text-right">Int</th>
            <th className="px-3 py-1 text-left">Tyre</th>
          </tr>
        </thead>

        <tbody className="bg-gray-950">
          {data.map((row) => {
            const isSelected = selectedDrivers.includes(
              row.driver_number
            )

            const gradient1 =
              DRIVER_GRADIENTS[row.team] ?? DEFAULT_GRADIENT
            const gradient2 =
              TEAM_GRADIENTS[row.team] ?? DEFAULT_GRADIENT

            return (
              <tr
                key={row.driver_number}
                onClick={() => onToggleDriver(row.driver_number)}
                className={`cursor-pointer border-t border-gray-800 transition-all duration-200 ${rowHeightClass} ${
                  isSelected
                    ? "ring-2 ring-white scale-[1.01]"
                    : "hover:bg-gray-900/60"
                }`}
              >
                <td className="px-3 py-1 whitespace-nowrap">
                  {row.position}
                </td>

                <td
                  className="px-3 py-1 font-medium whitespace-nowrap"
                  style={{ background: gradient1 }}
                >
                  {row.driver_code}
                </td>

                <td
                  className="px-3 py-1 whitespace-nowrap"
                  style={{ background: gradient2 }}
                >
                  {row.team}
                </td>

                <td className="px-3 py-1 text-right whitespace-nowrap">
                  {row.gap_to_leader === 0
                    ? "—"
                    : row.gap_to_leader > 100
                    ? "LAPPED"
                    : `+${row.gap_to_leader.toFixed(3)}`}
                </td>

                <td className="px-3 py-1 text-right whitespace-nowrap">
                  +{row.interval.toFixed(3)}
                </td>

                <td className="px-3 py-1 whitespace-nowrap">
                  <TyreBadge compound={row.tyre_compound} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}