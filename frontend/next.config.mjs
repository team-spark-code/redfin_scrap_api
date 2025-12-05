// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // 클라이언트 측에서 Node.js 모듈을 빈 객체로 대체
      config.resolve.fallback = {
        ...config.resolve.fallback,
        child_process: false,
        fs: false,
        path: false,
      };
    }
    return config;
  },
  crossOrigin: 'anonymous', // 소스맵 CORS 문제 완화
};

export default nextConfig;