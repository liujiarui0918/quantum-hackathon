import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/quantum/:path*',
        destination: 'http://localhost:8000/api/quantum/:path*',
      },
    ];
  },
};

export default nextConfig;
