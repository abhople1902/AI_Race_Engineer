import Link from "next/link"
import { REPLAY_SESSIONS } from "@/lib/replaySessions"

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto w-full max-w-6xl">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
          AI Race Engineer
        </h1>

        <div className="mt-8 h-px w-full bg-red-500/70" />

        <h2 className="mt-8 text-2xl font-semibold tracking-tight text-slate-100">
          F1 replay sessions
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Choose a race to load the replay of timing pages and race control. Predict strategies by selecting any two drivers.
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
        <p className="mt-2 text-sm text-slate-400">
          .......More races to come, along with the support for live races for the 2026 season
        </p>

        <div className="mt-10 h-px w-full bg-red-500/70" />

        <section className="mt-8 rounded-xl border border-slate-800/90 bg-slate-900/60 p-6">
          <h3 className="text-xl font-semibold tracking-tight text-slate-100">
            About AI Race engineer
          </h3>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            A web app that makes it easier to analyse the race as if talking to
            your F1 team's strategist. The application provides near real time
            replays for previous races and is currently in development for live
            races. Select any two of your drivers to compare them against
            strategies like undercut, overcoat, late undercut and much more all
            supported by the power of the LLM models called through OpenRouter.
          </p>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            The strategist will only get better with consideration of factors
            like flags during the race, pit stop durations, traffic and lapped
            cars traffic based decisions, all of this using model fine tuning.
            Then we have Vector DBs integration to analyse previous race data
            and predict current one. The list goes on making our AI strategist
            usable for race analysts and strategists.
          </p>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            Currently relying solely on OpenF1 data the application executes
            normalisation, and processing of the sparse data into a leaderboard
            readable by our AI model. All of this packed with cool looking
            aesthetics which will only get better overtime!
          </p>
        </section>

        <div className="mt-10 h-px w-full bg-red-500/70" />

        <footer className="mt-8 space-y-4 pb-2 text-sm text-slate-300">
          <p>
            Reach me at - {" "}
            <a
              href="mailto:apbhople19@gmail.com"
              className="text-red-300 underline decoration-red-400/80 underline-offset-2 transition hover:text-red-200"
            >
              apbhople19@gmail.com
            </a>
          </p>
          <p className="text-xs leading-6 text-slate-400">
            This website is not associated in any way with the Formula 1
            companies. F1, FORMULA ONE, FORMULA 1, FORMULA 1 ACADEMY, FIA
            FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are
            trade marks of Formula One Licensing B.V.
          </p>
          <p className="text-xs text-slate-500">© 2026 Ayush Bhople</p>
        </footer>
      </div>
    </main>
  )
}
