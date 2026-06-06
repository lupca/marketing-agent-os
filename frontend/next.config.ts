import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Clean config to avoid "Unrecognized key" warnings
  typescript: {
    ignoreBuildErrors: true,
  },
  allowedDevOrigins: ['192.168.0.200']
};

export default nextConfig;
