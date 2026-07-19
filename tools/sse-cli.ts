/**
 * sse-cli — a Node command-line client that streams the LangGraph agent's
 * SSE events live and prints each one, validated and typed.
 *
 * Usage:
 *   tsx tools/sse-cli.ts --message "I want a refund for the past 6 months"
 *   tsx tools/sse-cli.ts --url http://localhost:8000 --message "..." --vertical education
 *
 * Defaults to the public Cloud Run deployment (mock mode, no key, safe to hit).
 * Set LANGGRAPH_URL to point elsewhere. If the deployment is unreachable (e.g.
 * the free-trial URL has expired), the CLI prints actionable guidance instead
 * of a raw stack trace.
 */
import { streamChat, type AgentEvent } from "./sse-client.js";

const DEFAULT_URL =
  process.env.LANGGRAPH_URL ??
  "https://langgraph-platform-770658715879.australia-southeast1.run.app";

interface Args {
  url: string;
  message: string;
  session: string;
  vertical?: string;
}

function parseArgs(argv: string[]): Args {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a?.startsWith("--")) {
      const key = a.slice(2);
      const val = argv[i + 1];
      if (val !== undefined && !val.startsWith("--")) {
        out[key] = val;
        i += 1;
      } else {
        out[key] = "true";
      }
    }
  }
  return {
    url: out.url ?? DEFAULT_URL,
    message: out.message ?? "I want a refund for the past 6 months.",
    session: out.session ?? "cli-demo-session",
    vertical: out.vertical,
  };
}

// Minimal ANSI colour (no dependency) — one colour per event family.
const C = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  cyan: "\x1b[36m",
  yellow: "\x1b[33m",
  green: "\x1b[32m",
  red: "\x1b[31m",
};

function render(ev: AgentEvent): string {
  // The whole point of the discriminated union: exhaustive, type-checked cases.
  switch (ev.type) {
    case "thread":
      return `${C.dim}● thread${C.reset}      ${ev.thread_id}`;
    case "triage":
      return `${C.cyan}● triage${C.reset}      intent=${ev.intent} confidence=${ev.confidence} urgency=${ev.urgency}`;
    case "tool_call":
      return `${C.yellow}● tool_call${C.reset}   ${ev.tool}(${JSON.stringify(ev.arguments)})`;
    case "tool_result":
      return `${C.yellow}● tool_result${C.reset} ${ev.tool} → ${JSON.stringify(ev.result).slice(0, 100)}`;
    case "token":
      return `${C.green}● token${C.reset}       ${JSON.stringify(ev.delta)}`;
    case "human_escalation":
      return `${C.red}● escalation${C.reset}  reason=${ev.reason} draft_quality=${ev.draft_quality}`;
    case "done":
      return `${C.dim}● done${C.reset}        latency=${ev.latency_ms}ms tokens=${ev.tokens} mode=${ev.mode}`;
    case "error":
      return `${C.red}● error${C.reset}       ${ev.message}`;
    default: {
      // Exhaustiveness guard: adding a new event type without handling it here
      // becomes a compile error.
      const _never: never = ev;
      return `unknown ${JSON.stringify(_never)}`;
    }
  }
}

async function preflight(url: string): Promise<void> {
  // A quick, well-explained reachability check so an expired/dead deployment
  // produces guidance instead of a cryptic stream error mid-run.
  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/api/health`, {
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    console.error(`${C.red}Deployment unreachable:${C.reset} ${url} (${reason})`);
    console.error(
      `${C.dim}The public demo URL is backed by a free trial and may have expired.\n` +
        `Run the server locally and retry:\n` +
        `  (cd .. && uvicorn api.main:app --port 8000)\n` +
        `  npm run cli -- --url http://localhost:8000 --message "..."${C.reset}`,
    );
    process.exit(2);
  }
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  await preflight(args.url);

  console.log(`${C.dim}POST ${args.url}/api/chat${C.reset}`);
  console.log(`${C.dim}message: ${args.message}${C.reset}\n`);

  const counts: Record<string, number> = {};
  const tokens: string[] = [];

  for await (const ev of streamChat(args.url, {
    message: args.message,
    session_id: args.session,
    vertical: args.vertical,
  })) {
    counts[ev.type] = (counts[ev.type] ?? 0) + 1;
    if (ev.type === "token") tokens.push(ev.delta);
    console.log(render(ev));
  }

  console.log(`\n${C.dim}── stream closed ──${C.reset}`);
  console.log("event counts:", counts);
  if (tokens.length) console.log("assembled reply:", tokens.join(""));
}

main().catch((err) => {
  console.error(`${C.red}stream error:${C.reset}`, err instanceof Error ? err.message : err);
  process.exit(1);
});
