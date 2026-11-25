import type { Metadata } from "next";
import Link from "next/link";
import { Shield } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "NoticeSetu — Multilingual Campus Notice Intelligence",
  description:
    "Convert official college circulars (PDFs, photos, or portal URLs) into source-checked Action Cards in English, Hindi, and Marathi.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F8FAFC] text-[#0F172A] antialiased">
        <header className="no-print border-b border-slate-200 bg-[#0F172A] text-white">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3.5">
            <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#0D9488] text-sm font-extrabold text-white">
                NS
              </span>
              <span className="text-base">NoticeSetu</span>
            </Link>

            <nav className="flex items-center gap-4 text-xs font-medium text-slate-200">
              <Link href="/" className="hover:text-white">
                Hub
              </Link>
              <Link href="/widget-demo" className="hover:text-white">
                College Widget Demo
              </Link>
              <span className="hidden items-center gap-1 rounded-full border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] text-teal-300 sm:inline-flex">
                <Shield className="h-3 w-3" />
                Zero Login • In-Memory
              </span>
            </nav>
          </div>
        </header>

        <main className="mx-auto max-w-4xl px-4 py-6 sm:py-8">{children}</main>

        <footer className="no-print border-t border-slate-200 bg-white py-5 text-center text-xs text-slate-600">
          <div className="mx-auto max-w-4xl px-4">
            <p className="font-medium text-slate-800">
              NoticeSetu — Assistive Campus Notice Reader (English • हिंदी • मराठी)
            </p>
            <p className="mt-1">
              Zero student accounts. Raw uploads stay in RAM only and cached notices expire after 14 days.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

