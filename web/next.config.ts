import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // The console lives in web/ inside the langgraph-platform repository and
  // imports the typed SSE protocol straight from ../tools/sse-client.ts —
  // one schema source for the CLI, the Node tests and this UI. Turbopack
  // resolves nothing outside its root, so the root must be the repository.
  turbopack: {
    root: path.join(__dirname, ".."),
  },

  async rewrites() {
    // Dev-time proxy to a running engine (local uvicorn, or the deployed
    // demo when no local engine is up). In production Vercel routes
    // /api/* to the FastAPI function before requests reach Next, so this
    // rewrite never fires there.
    const engine =
      process.env.ENGINE_ORIGIN ?? "https://langgraph-platform-demo.vercel.app";
    return [{ source: "/api/:path*", destination: `${engine}/api/:path*` }];
  },
};

export default nextConfig;
