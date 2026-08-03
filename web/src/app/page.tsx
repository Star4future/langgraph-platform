import { Console } from "@/components/console";

const REPO = "https://github.com/Star4future/langgraph-platform";

const LINKS = [
  { label: "API docs", href: "/api/docs" },
  { label: "Health", href: "/api/health" },
  { label: "Architecture", href: `${REPO}/blob/main/ARCHITECTURE.md` },
  { label: "Expert review", href: `${REPO}/blob/main/EXPERT-REVIEW.md` },
];

// Numbers verified against the repository: verticals/education/tools.py
// defines eight tools; eval/datasets/education_30.jsonl holds thirty
// scenarios; tools/sse-client.ts models the eight-variant event union.
const FACTS = [
  { k: "education tools", v: "8" },
  { k: "eval scenarios", v: "30" },
  { k: "SSE event types", v: "8" },
  { k: "layering gate", v: "AST test" },
];

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
      <section className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Agent workflow console
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-dim sm:text-base">
          A live view into the Triage → Resolver → Supervisor graph: every server-sent event
          rendered as it arrives, with the run pipeline beside it. Education vertical loaded;
          responses come from the engine&apos;s deterministic mock mode.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          {LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              target="_blank"
              rel="noreferrer"
              className="text-ink-dim underline decoration-line underline-offset-4 transition-colors hover:text-ink"
            >
              {l.label} ↗
            </a>
          ))}
          <span className="hidden h-3 w-px bg-line sm:inline-block" />
          {FACTS.map((f) => (
            <span key={f.k} className="text-ink-dim">
              <span className="font-mono text-ink">{f.v}</span> {f.k}
            </span>
          ))}
        </div>
      </section>

      <Console />
    </main>
  );
}
