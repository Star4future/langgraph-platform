import type { Metadata } from "next";

export const metadata: Metadata = { title: "Evals" };

export default function EvalsPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Smoke-eval results</h1>
      <p className="mt-2 text-sm text-ink-dim">
        Rendering of the repository&apos;s committed eval artefacts lands here.
      </p>
    </main>
  );
}
