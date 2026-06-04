import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import SystemDiagnosticsOverlay from "@/components/SystemDiagnosticsOverlay";
import { AuthProvider } from "@/contexts/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Marketing Agent OS - Autonomous MAB Creative Intelligence Engine",
  description: "Stateless Autonomous Creative Intelligence Engine powered by LangGraph, Multi-Armed Bandit logic, and Relational OLAP.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <SystemDiagnosticsOverlay />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

