import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Clean config to avoid "Unrecognized key" warnings
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
