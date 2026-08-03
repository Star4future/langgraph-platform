"use client";

/**
 * The header badge is an instrument, not a sticker: it reports what
 * GET /api/health says about this deployment (mock vs real LLM, engine
 * version) instead of hardcoding a claim. Second and final 'use client'
 * boundary in the app — it holds fetch state.
 */
import { useEffect, useState } from "react";

type Health =
  { kind: "loading" } | { kind: "unreachable" } | { kind: "ok"; mode: string; version: string };

/**
 * Runtime check instead of a type assertion — same discipline the stream
 * gets from zod. A hand-rolled guard rather than a zod schema on purpose:
 * "zod" here would resolve from web/node_modules while the protocol's
 * schemas resolve theirs from tools/node_modules, bundling a second zod
 * for one three-field object.
 */
function parseHealth(x: unknown): { mode: string; version: string } | null {
  if (typeof x !== "object" || x === null) return null;
  const mode = (x as Record<string, unknown>).mode;
  const version = (x as Record<string, unknown>).version;
  return typeof mode === "string" && typeof version === "string" ? { mode, version } : null;
}

export function HealthBadge() {
  const [health, setHealth] = useState<Health>({ kind: "loading" });

  useEffect(() => {
    let alive = true;
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j: unknown) => {
        if (!alive) return;
        const parsed = parseHealth(j);
        // An answer that doesn't look like the health contract is treated
        // the same as no answer — the badge never renders trusted garbage.
        setHealth(parsed ? { kind: "ok", ...parsed } : { kind: "unreachable" });
      })
      .catch(() => {
        if (alive) setHealth({ kind: "unreachable" });
      });
    return () => {
      alive = false;
    };
  }, []);

  const base =
    "rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-semibold tracking-wide";

  if (health.kind === "loading") {
    return (
      <span className={`${base} border-line text-ink-dim`} title="Checking /api/health…">
        MODE …
      </span>
    );
  }
  if (health.kind === "unreachable") {
    return (
      <span
        className={`${base} border-err/50 bg-err/10 text-err`}
        title="/api/health did not answer"
      >
        ENGINE OFFLINE
      </span>
    );
  }
  const mock = health.mode === "mock";
  return (
    <span
      className={`${base} ${mock ? "border-warn/50 bg-warn/10 text-warn" : "border-ok/50 bg-ok/10 text-ok"}`}
      title={`Reported by GET /api/health — engine v${health.version}. ${
        mock
          ? "No LLM key on this deployment; responses come from the deterministic mock."
          : "A real LLM key is configured."
      }`}
    >
      {mock ? "MOCK MODE" : "LIVE MODE"}
    </span>
  );
}
