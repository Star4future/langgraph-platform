# Web console

Next.js front end for the LangGraph Platform engine: a streaming chat console, a live
run-pipeline panel, and a rendered view of the committed eval artefacts. Everything on
screen is driven by the same typed SSE protocol the CLI and the Node tests consume —
one schema source, in [`../tools/sse-client.ts`](../tools/sse-client.ts).

**Stack:** Next.js 16 (App Router, Turbopack) · React 19 · TypeScript (strict) · Tailwind 4 · vitest + Testing Library.

## Run it

```bash
# 1. The protocol package first — the console imports ../tools/sse-client.ts,
#    whose zod resolves from tools/node_modules.
cd tools && npm ci && cd ../web

# 2. Install and start the console
npm ci
npm run dev            # http://localhost:3000
```

By default `next dev` proxies `/api/*` to the deployed demo engine, so the console
works out of the box with no Python running. To develop against a local engine
(`uvicorn core.api.main:app --port 8000`, see the root README's Quick Start):

```bash
ENGINE_ORIGIN=http://localhost:8000 npm run dev
```

In production the proxy never fires — Vercel routes `/api/*` to the FastAPI function
before requests reach Next.

```bash
npm run typecheck      # tsc --noEmit
npm test               # vitest (reducer, pipeline projection, rendering contracts)
npm run lint           # eslint (eslint-config-next)
npm run format:check   # prettier, same config as tools/
npm run build          # production build — all routes prerender static
```

## How it's put together

```
src/lib/protocol.ts        →  re-exports ../tools/sse-client.ts (single schema source;
                              the only file in web/ that reaches outside the app)
src/lib/transport.ts       →  fetch POST /api/chat + readAgentStream + AbortSignal
src/lib/stream-reducer.ts  →  pure state machine: wire facts in, one derived
                              projection (derivePipeline) for the panel
src/lib/eval-data.ts       →  build-time reader/parser for eval/EVAL-RESULTS.md
                              and eval/datasets/education_30.jsonl
src/components/…           →  Console (client boundary) + presentational views
src/app/…                  →  / console · /evals artefact render · /about
```

The flow for one run: the Console island POSTs `/api/chat`, pumps validated
`AgentEvent`s through the reducer as they arrive, and every visible element — timeline
cards, streamed answer, pipeline node states — is a projection of that reducer state.
No timers, no choreographed progress: the protocol only carries _completion_ events
(the server emits on each node's `on_chain_end`), so "running" is always an inference
from the previous stage having finished, and that inference lives in exactly one
function (`derivePipeline`), where the tests can pin it.

## Server/client split — the full ledger

Layouts and pages are server components by default; interactivity is opted into per
file. Every `'use client'` directive in the app, with its reason:

| File                              | Why it must be client                                                                                                                                                      |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/components/console.tsx`      | Owns `useReducer`, the AbortController, session id, scroll/focus refs — the one interactive boundary; everything it renders ships in its bundle without further directives |
| `src/components/health-badge.tsx` | Fetches `/api/health` after mount and holds that state, so the badge reports the engine's actual mode instead of a hardcoded claim                                         |

Everything else — `/evals` (reads committed artefacts at build time and prerenders),
`/about`, the layout chrome — renders on the server. `RunView` and `PipelinePanel`
carry no directive: they're presentational modules imported by the Console boundary.

## Why Next.js and not a Vite SPA

- The evals page is the honest argument: it renders _committed artefacts_ at build
  time (RSC + `fs.readFile`), ships zero client JavaScript for that route, and can
  never drift from the files it renders. In a SPA that's a fetch, a loading state and
  a second copy of the numbers.
- One deployment story for the whole surface — static prerender for content routes,
  a client island where interactivity is real, and the platform's `/api/*` routing
  underneath.
- Candidly: Next is also the ecosystem default the market speaks. The console doubles
  as a reference implementation of the RSC-boundary and streaming patterns above.

## Next 16 notes (read before writing code)

This app was written against the docs bundled in `node_modules/next/dist/docs/`
(the version actually installed — Next 16 differs from what most tutorials and
training data describe). The guides that shaped this code:

- `01-getting-started/05-server-and-client-components.md` — boundary rules above
- `02-guides/upgrading/version-16.md` — Turbopack is the default bundler for dev and
  build; async request APIs are mandatory (this app uses none); middleware is renamed
  proxy (unused here); React Compiler is stable but opt-in (not enabled)
- `03-api-reference/05-config/01-next-config-js/turbopack.md` — Turbopack resolves
  nothing outside its root; `turbopack.root` points at the repository so the
  cross-package protocol import works (see `next.config.ts`)
- `02-guides/caching-without-cache-components.md` — the classic caching model applies
  (`cacheComponents` not enabled); routes with no dynamic APIs prerender static
- `01-getting-started/16-proxy.md` / `10-error-handling.md` / `06-fetching-data.md`

Two deliberate configuration calls, both documented inline in
[`next.config.ts`](next.config.ts): `turbopack.root` for the monorepo import, and
`compress: false` because gzip buffers proxied SSE (found the hard way — the browser
advertises gzip, curl doesn't, so curl-based checks looked fine while the browser saw
nothing until the stream closed).

## Testing

`vitest run` — 28 behavioural cases in three files, all driven through the real
reducer with wire-shaped fixtures captured from the deployed engine:

- `stream-reducer.test.ts` — happy path, retry-pass grouping, escalation, the
  error-then-done epilogue, mid-stream transport failure, abort semantics, retry
  keeping the user message, send guards
- `derive-pipeline.test.ts` — what the panel shows at every stage of a run, including
  the honest edges (cancelled runs don't invent completion or verdicts)
- `run-view.test.tsx` (jsdom) — error states expose a working retry, partial output
  survives cancellation, escalation copy carries the draft score

The suite tests behaviour, not implementation: it would catch a dropped `done`
epilogue or a panel that claims work it never observed, and did catch both while
being written.
