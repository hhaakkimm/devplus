import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // cacheComponents stays off: the auth layout reads cookies, which fails the build with it on.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  // The package ships TS sources.
  transpilePackages: ["@devplus/api-client"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
    ],
  },
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_INTERNAL_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
