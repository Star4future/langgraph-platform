import type { Metadata } from "next";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">About this console</h1>
      <p className="mt-2 text-sm text-ink-dim">
        What this deployment is — and deliberately is not.
      </p>
    </main>
  );
}
