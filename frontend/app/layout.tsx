import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

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
            <header className="border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur sticky top-0 z-50">
              <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-sm">
                    EQ
                  </div>
                  <span className="font-semibold text-lg tracking-tight">
                    EquiTest NSE
                  </span>
                </div>
                <nav className="flex items-center space-x-6 text-sm font-medium">
                  <a
                    href="/"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Home
                  </a>
                  <a
                    href="/data"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Data Status
                  </a>
                  <a
                    href="/indicators"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Indicators
                  </a>
                  <a
                    href="/signals"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Signals
                  </a>
                  <a
                    href="/risk"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Risk
                  </a>
                  <a
                    href="/backtest"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Backtest
                  </a>
                  <a
                    href="/sweep"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Sweep
                  </a>
                  <a
                    href="/reports/test-run-123"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Reports
                  </a>
                  <a
                    href="/validation"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Validation
                  </a>
                  <a
                    href="/docs"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    Docs
                  </a>
                  <a
                    href="/api-health"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
                  >
                    API Health
                  </a>
                </nav>
              </div>
            </header>
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
