import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RedFin RSS Admin",
  description: "RSS 관리 페이지",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
