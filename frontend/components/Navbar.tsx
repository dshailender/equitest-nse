"use client";

import React, { useState } from "react";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/data", label: "Data Status" },
  { href: "/indicators", label: "Indicators" },
  { href: "/signals", label: "Signals" },
  { href: "/risk", label: "Risk" },
  { href: "/backtest", label: "Backtest" },
  { href: "/sweep", label: "Sweep" },
  { href: "/reports", label: "Reports" },
  { href: "/validation", label: "Validation" },
  { href: "/docs", label: "Docs" },
  { href: "/api-health", label: "API Health" },
];

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
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

        {/* Desktop Nav */}
        <nav className="hidden xl:flex items-center space-x-5 text-sm font-medium">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Mobile / Tablet Menu Button */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="xl:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Toggle navigation menu"
          aria-expanded={isOpen}
          data-testid="btn-toggle-menu"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {isOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile / Tablet Dropdown Menu */}
      {isOpen && (
        <nav
          className="xl:hidden px-4 pt-2 pb-4 border-t border-slate-200 dark:border-slate-800 space-y-1 bg-white/95 dark:bg-slate-900/95"
          data-testid="mobile-menu"
        >
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setIsOpen(false)}
              className="block px-3 py-2 rounded-md text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}
