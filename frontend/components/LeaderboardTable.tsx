import { LeaderboardEntry } from "@/lib/types"
import TyreBadge from "./tyreBadge"

type Props = {
  data: LeaderboardEntry[]
}

export default function LeaderboardTable({ data }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
      <table className="min-w-full text-sm text-gray-900 dark:text-gray-100">
        <thead className="bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300">
          <tr>
            <th className="px-3 py-2 text-left">Pos</th>
            <th className="px-3 py-2 text-left">Driver</th>
            <th className="px-3 py-2 text-left">Team</th>
            <th className="px-3 py-2 text-right">Gap</th>
            <th className="px-3 py-2 text-right">Interval</th>
            <th className="px-3 py-2 text-left">Tyre</th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-950">
          {data.map((row) => (
            <tr
              key={row.driver_number}
              className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <td className="px-3 py-2">{row.position}</td>
              <td className="px-3 py-2 font-medium">
                {row.driver_code}
              </td>
              <td className="px-3 py-2">{row.team}</td>
              <td className="px-3 py-2 text-right">
                {row.gap_to_leader === 0
                  ? "—"
                  : `+${row.gap_to_leader.toFixed(3)}`}
              </td>
              <td className="px-3 py-2 text-right">
                +{row.interval.toFixed(3)}
              </td>
              <td className="px-3 py-2">
                <TyreBadge compound={row.tyre_compound} />
              </td>

            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}