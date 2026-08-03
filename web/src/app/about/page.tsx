import type { Metadata } from "next";

export const metadata: Metadata = { title: "About" };

const REPO = "https://github.com/Star4future/langgraph-platform";

const STACK: [string, string][] = [
  ["Engine", "LangGraph 0.2 · FastAPI · Python — industry-agnostic core/, pluggable verticals/"],
  ["Protocol", "8-variant AgentEvent union, zod-validated, defined once in tools/sse-client.ts"],
  ["Console", "Next.js 16 (App Router, Turbopack) · React 19 · TypeScript · Tailwind 4"],
  ["Streaming", "POST /api/chat → text/event-stream, consumed with fetch + AbortController"],
  ["State", "useReducer over wire facts; pipeline view is a pure projection of them"],
  ["Vertical", "Education — 8 domain tools, 30-scenario smoke dataset"],
];

const LINKS: [string, string][] = [
  ["Repository", REPO],
  ["Architecture", `${REPO}/blob/main/ARCHITECTURE.md`],
  ["Expert review + resolution log", `${REPO}/blob/main/EXPERT-REVIEW.md`],
  ["Experience log (how v1 was built)", `${REPO}/blob/main/EXPERIENCE-LOG.md`],
  ["API docs (FastAPI)", "/api/docs"],
];

export default function AboutPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">About this console</h1>

      <section className="mt-4 space-y-3 text-sm leading-6 text-ink-dim">
        <p>
          This deployment is the <span className="text-ink">reference implementation</span> of{" "}
          <a href={REPO} className="underline decoration-line underline-offset-2 hover:text-ink">
            langgraph-platform
          </a>{" "}
          — a multi-agent customer-workflow engine with an industry-agnostic core and pluggable
          verticals — plus this console, a Next.js front end that renders the engine&apos;s event
          stream as it arrives. The chat, the pipeline panel and the timeline are all driven by one
          typed SSE protocol whose schema lives in a single file shared by the CLI, the test suite
          and this UI.
        </p>
        <p>
          <span className="text-ink">It runs in mock mode on purpose.</span> No LLM key is
          configured here, so the engine answers from a deterministic keyword-matched mock. That
          keeps the demo free, fast and reproducible — and it means what you are watching is the{" "}
          <em>pipeline</em>: triage, tool dispatch, supervisor scoring, the retry loop, human
          escalation on a checkpoint. Streaming, however, is real — open the network tab and
          you&apos;ll find one text/event-stream response per run, not a choreographed animation.
        </p>
        <p>
          <span className="text-ink">What&apos;s deliberately absent:</span> authentication, a
          database, real LLM calls, rate limiting, multi-tenancy — and a durable checkpoint store,
          so paused escalations live only as long as the serverless worker that holds them. Taking
          this to production is exactly the interesting conversation — auth in front, a real engine
          deployment behind a stable origin, backpressure on the stream, tracing and cost controls
          on every model call. The repository&apos;s expert review tracks which of those gaps are
          closed and which stay open by design.
        </p>
        <p>
          <span className="text-ink">About that expert review:</span> v1 was put through a
          commissioned adversarial review, published verbatim — including a 2/5 for production
          readiness and a 2/5 for eval rigour — with a resolution log recording what each finding
          became. Publishing the scores next to the fixes is the point: the demo badge says mock,
          the evals page says smoke test, and the review says where the edges are.
        </p>
      </section>

      <h2 className="mt-8 text-lg font-medium">The stack, concretely</h2>
      <div className="mt-3 overflow-x-auto rounded-lg border border-line">
        <table className="w-full text-sm">
          <tbody>
            {STACK.map(([k, v]) => (
              <tr key={k} className="border-t border-line first:border-t-0">
                <td className="whitespace-nowrap px-3.5 py-2.5 text-xs font-medium text-ink">
                  {k}
                </td>
                <td className="px-3.5 py-2.5 text-xs leading-5 text-ink-dim">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="mt-8 text-lg font-medium">Read the source</h2>
      <ul className="mt-3 space-y-1.5 text-sm">
        {LINKS.map(([label, href]) => (
          <li key={label}>
            <a
              href={href}
              className="text-ink-dim underline decoration-line underline-offset-4 transition-colors hover:text-ink"
            >
              {label} ↗
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
