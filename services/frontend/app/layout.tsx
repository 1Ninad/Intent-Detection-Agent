import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Intent Detection Agent",
  description: "B2B Intent Detection for Sales Teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
