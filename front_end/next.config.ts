import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals = config.externals || [];
      if (Array.isArray(config.externals)) {
        config.externals.push('ssh2');
      }
    }
    return config;
  },
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
