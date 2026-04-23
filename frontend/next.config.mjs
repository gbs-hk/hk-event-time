/** @type {import('next').NextConfig} */
const isProduction = process.env.NODE_ENV === "production";

const nextConfig = {
  reactStrictMode: true,
  ...(isProduction ? { output: "export" } : {})
};

if (!isProduction) {
  nextConfig.rewrites = async () => [
    {
      source: "/api/:path*",
      destination: "http://127.0.0.1:8000/api/:path*"
    }
  ];
}

export default nextConfig;
