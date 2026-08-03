import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { HealthBadge } from "@/components/health-badge";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "LangGraph Platform — Console",
    template: "%s · LangGraph Platform",
  },
  description:
    "Interactive console for a production-patterned multi-agent customer workflow engine. Industry-agnostic core, pluggable verticals, typed SSE protocol.",
};

const REPO_URL = "https://github.com/Star4future/langgraph-platform";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-bg text-ink">
        <header className="sticky top-0 z-20 border-b border-line bg-bg/80 backdrop-blur">
          <div className="mx-auto flex w-full max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-accent" />
              <span>LangGraph Platform</span>
              <span className="hidden text-ink-dim sm:inline">/ console</span>
            </Link>
            <nav className="ml-auto flex items-center gap-1 text-sm">
              <Link
                href="/"
                className="rounded-md px-2.5 py-1.5 text-ink-dim transition-colors hover:bg-surface hover:text-ink"
              >
                Console
              </Link>
              <Link
                href="/evals"
                className="rounded-md px-2.5 py-1.5 text-ink-dim transition-colors hover:bg-surface hover:text-ink"
              >
                Evals
              </Link>
              <Link
                href="/about"
                className="rounded-md px-2.5 py-1.5 text-ink-dim transition-colors hover:bg-surface hover:text-ink"
              >
                About
              </Link>
            </nav>
            {/* Honesty layer: the badge reports /api/health on every page
                instead of hardcoding a claim about the deployment. */}
            <HealthBadge />
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="hidden rounded-md border border-line px-2.5 py-1 text-sm text-ink-dim transition-colors hover:border-accent hover:text-ink sm:inline-block"
            >
              GitHub ↗
            </a>
          </div>
        </header>

        <div className="flex-1">{children}</div>

        <footer className="border-t border-line py-6 text-center text-xs text-ink-dim">
          <p>
            Reference implementation, mock mode — engine:{" "}
            <a
              href={REPO_URL}
              className="underline decoration-line underline-offset-2 hover:text-ink"
            >
              github.com/Star4future/langgraph-platform
            </a>
          </p>
          <p className="mt-1">
            LangGraph 0.2 · FastAPI · Next.js · single typed SSE protocol source · MIT
          </p>
        </footer>
      </body>
    </html>
  );
}
