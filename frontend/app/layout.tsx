import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Knowledge Wiki - MongoDB RAG Agent",
  description:
    "Generate interactive wikis from your ingested knowledge base using RAG",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
