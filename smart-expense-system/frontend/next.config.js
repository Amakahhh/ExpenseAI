/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === "production";
const backendUrl = process.env.BACKEND_URL ||
  (isProd ? "https://expenseai-ivoh.onrender.com" : "http://localhost:8000");

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
