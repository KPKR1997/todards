import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Todards · Pipeline Observatory",
  description: "Read-only LLM and content pipeline observability for Todards.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
