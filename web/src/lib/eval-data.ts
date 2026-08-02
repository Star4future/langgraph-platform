/**
 * Build-time reader for the repository's committed eval artefacts:
 *
 *   eval/EVAL-RESULTS.md           — generated output of eval/run_eval.py
 *   eval/datasets/education_30.jsonl — the 30-scenario smoke dataset
 *
 * The evals page is a server component with no dynamic APIs, so Next
 * prerenders it at build time; these reads never happen per-request.
 * Every number shown on the page is parsed from those two files — nothing
 * is restated by hand, so the page can't drift from the artefacts.
 *
 * The markdown parser is deliberately narrow: run_eval.py emits stable
 * pipe tables under known headings, and this module targets exactly that
 * shape (a format change should break the build here, loudly).
 */
import fs from "node:fs/promises";
import path from "node:path";

export interface MetricRow {
  metric: string;
  value: string;
  threshold: string;
  pass: boolean;
}

export interface BreakdownRow {
  key: string;
  count: number;
  passed: number;
  rate: string;
}

export interface ScenarioResult {
  id: string;
  category: string;
  difficulty: string;
  pass: boolean;
  intent: boolean;
  tools: boolean;
  human: boolean;
  quality: string;
  latency: string;
}

export interface Scenario {
  id: string;
  input: string;
  expected_intent: string;
  expected_tools: string[];
  should_require_human: boolean;
  quality_threshold: number;
}

export interface EvalData {
  runAt: string;
  metrics: MetricRow[];
  byCategory: BreakdownRow[];
  byDifficulty: BreakdownRow[];
  scenarios: (ScenarioResult & { scenario: Scenario | null })[];
}

/** web/ builds with cwd=web locally and on Vercel; fall back defensively. */
async function repoRoot(): Promise<string> {
  for (const candidate of [path.join(process.cwd(), ".."), process.cwd()]) {
    try {
      await fs.access(path.join(candidate, "eval", "datasets", "education_30.jsonl"));
      return candidate;
    } catch {
      /* try next */
    }
  }
  throw new Error(
    "eval artefacts not found — is eval/datasets/education_30.jsonl excluded from the deployment?",
  );
}

function rows(section: string): string[][] {
  return section
    .split("\n")
    .filter((l) => l.trim().startsWith("|"))
    .map((l) => l.split("|").slice(1, -1).map((c) => c.trim()))
    .filter((cells) => !cells[0]?.startsWith("---") && !cells[0]?.startsWith(":"))
    .slice(1); // drop the header row
}

function section(md: string, heading: string): string {
  const start = md.indexOf(heading);
  if (start === -1) throw new Error(`EVAL-RESULTS.md: missing section "${heading}"`);
  const rest = md.slice(start + heading.length);
  const next = rest.indexOf("\n## ");
  return next === -1 ? rest : rest.slice(0, next);
}

export async function loadEvalData(): Promise<EvalData> {
  const root = await repoRoot();
  const [md, jsonl] = await Promise.all([
    fs.readFile(path.join(root, "eval", "EVAL-RESULTS.md"), "utf8"),
    fs.readFile(path.join(root, "eval", "datasets", "education_30.jsonl"), "utf8"),
  ]);

  const runAt = md.match(/\*\*Run at:\*\* (.+)/)?.[1]?.trim() ?? "unknown";

  const metrics: MetricRow[] = rows(section(md, "## Summary metrics")).map((c) => ({
    metric: c[0],
    value: c[1],
    threshold: c[2],
    pass: c[3]?.includes("PASS") ?? false,
  }));

  const breakdown = (heading: string): BreakdownRow[] =>
    rows(section(md, heading)).map((c) => ({
      key: c[0],
      count: Number(c[1]),
      passed: Number(c[2]),
      rate: c[3],
    }));

  const scenarios = new Map<string, Scenario>(
    jsonl
      .split("\n")
      .filter((l) => l.trim())
      .map((l) => {
        const s = JSON.parse(l) as Scenario;
        return [s.id, s];
      }),
  );

  const results: EvalData["scenarios"] = rows(section(md, "## Per-scenario results")).map(
    (c) => ({
      id: c[0],
      category: c[1],
      difficulty: c[2],
      pass: c[3] === "✓",
      intent: c[4] === "✓",
      tools: c[5] === "✓",
      human: c[6] === "✓",
      quality: c[7],
      latency: c[8],
      scenario: scenarios.get(c[0]) ?? null,
    }),
  );

  return {
    runAt,
    metrics,
    byCategory: breakdown("## By category"),
    byDifficulty: breakdown("## By difficulty"),
    scenarios: results,
  };
}
