import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/wiki/:path*",
        destination: "http://localhost:8000/api/v1/wiki/:path*",
      },
      {
        source: "/api/query/:path*",
        destination: "http://localhost:8000/api/v1/query/:path*",
      },
      {
        source: "/api/health/:path*",
        destination: "http://localhost:8000/api/v1/health/:path*",
      },
    ];
  },
};

export default nextConfig;
