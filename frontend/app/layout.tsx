import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Navbar } from "../components/Navbar";

const inter = { className: "font-sans" };

export const metadata: Metadata = {
  title: "EquiTest NSE - Backtesting Framework",
  description:
    "Quantitative backtesting framework for Indian equities (NSE 101-750)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col">
            <Navbar />
            <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8">
              {children}
            </main>
            <footer className="border-t border-slate-200 dark:border-slate-800 py-6 text-center text-xs text-slate-500">
              EquiTest NSE • Phase 0 Scaffolding • Indian Equities Quantitative Framework
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
