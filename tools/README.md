# tools/ — Typed, zod-validated SSE client + Node CLI

A **TypeScript** client for this platform's agent event stream, plus a Node CLI
that consumes the live deployment, plus the browser bundle the shipping demo
page imports.

`POST /api/chat` returns Server-Sent Events (`core/api/sse.py`). This turns that
untyped `data: {...}` wire format into a **zod-validated discriminated union**
(`AgentEvent`, eight variants) so a consumer can `switch (event.type)` with the
compiler enforcing exhaustive handling — and a malformed payload is **rejected
at runtime**, not silently trusted. "Typed" here means validated, not cast.

## Event coverage — what we type is what ships

The union models the **eight events the server actually emits** (verified against
`core/api/main.py`): `thread`, `triage`, `tool_call`, `tool_result`, `token`,
`human_escalation`, `done`, `error`. The `citations` helper declared in
`core/api/sse.py` is deliberately **not** modelled — the customer-support graph
never emits it; it is reserved for a future source-grounded vertical.

## Files

| File               | Role                                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| `sse-client.ts`    | zod schemas + `AgentEvent` union (8 types), SSE block parser, chunk-safe stream reader, `streamChat()` |
| `sse-cli.ts`       | Node CLI: preflight health check, then prints each typed event live + a summary                        |
| `web-entry.ts`     | browser entry — esbuild bundles it (+ zod) into `../web/sse-client.mjs`, the standalone browser build  |
| `test/sse.test.ts` | Vitest — parse every event type, reject malformed payloads, reassemble split chunks                    |

## Run

```bash
cd tools
npm install

# Stream the live Cloud Run deployment (mock mode, no key needed).
# A refund question exercises tool_call / tool_result:
npm run cli -- --message "I want a refund for the past 6 months"

# Point at a local server instead:
LANGGRAPH_URL=http://localhost:8000 npm run cli -- --message "..."

npm test           # parser + validation unit tests (deterministic, offline)
npm run typecheck
npm run lint
npm run build:web  # rebuild the browser bundle the demo page imports
```

If the deployment is unreachable (e.g. the free-trial URL expired), the CLI
prints actionable guidance and exits, instead of a raw stack trace.

## The event protocol

```ts
type AgentEvent =
  | { type: "thread"; thread_id: string }
  | { type: "triage"; intent: string; confidence: number; urgency: string }
  | { type: "tool_call"; tool: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; tool: string; result: unknown }
  | { type: "token"; delta: string }
  | { type: "human_escalation"; session_id: string; reason: string; draft_quality: number }
  | { type: "done"; latency_ms: number; tokens: number; mode: string }
  | { type: "error"; message: string };
```

Each variant is a zod schema; `AgentEvent` is inferred from the schemas (one
source of truth). The CLI's `render()` switch has an exhaustiveness guard
(`const _never: never`), so adding an event type without handling it is a
compile error.

## Consumers

The Next.js console in `web/` imports `sse-client.ts` directly — schema, parser
and stream reader from this one file drive its chat UI, so the protocol has a
single source of truth across the CLI, the tests and the front end. The bundled
`../web/sse-client.mjs` (built from `web-entry.ts`) remains published at
`/sse-client.mjs` by a route in `api/main.py` as the standalone browser build —
drop it into any page and call `streamChat` without a build step; it powered the
original single-file demo page before the console replaced it. CI rebuilds the
bundle and fails if the committed copy has drifted.
