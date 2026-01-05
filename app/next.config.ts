import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  serverExternalPackages: ['openai'],
  eslint: {
    // Don't fail build on ESLint errors during production builds
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Don't fail build on TypeScript errors (we've fixed the critical ones)
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
