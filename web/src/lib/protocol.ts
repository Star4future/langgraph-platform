/**
 * Single protocol source.
 *
 * The agent event stream is defined once, in tools/sse-client.ts, as a
 * zod-validated discriminated union — the same module the Node CLI and the
 * vitest suite consume. The console re-exports it instead of declaring its
 * own event types, so a protocol change breaks the build here rather than
 * silently drifting. This file is deliberately the only place in web/ that
 * reaches outside the app directory.
 */
export * from "../../../tools/sse-client";
