import Link from "next/link"
import { REPLAY_SESSIONS } from "@/lib/replaySessions"

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto w-full max-w-6xl">
        <h1 className="text-3xl font-semibold tracking-tight">
          F1 Replay Sessions
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Choose a race to load the replay workspace.
        </p>

        <section className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {REPLAY_SESSIONS.map((session) => (
            <Link
              key={session.id}
              href={`/replay/${session.id}`}
              className="group rounded-xl border border-slate-800 bg-slate-900/70 p-6 transition hover:border-sky-400/40 hover:bg-slate-900"
            >
              <div className="text-xs uppercase tracking-[0.18em] text-sky-300/80">
                Replay
              </div>
              <div className="mt-3 text-2xl font-semibold text-white">
                {session.name}
              </div>
              <div className="mt-1 text-sm text-slate-300">
                {session.subtitle}
              </div>
            </Link>
          ))}
        </section>
      </div>
    </main>
  )
}
