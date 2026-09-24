"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchSignals,
  screenUniverse,
  type SignalItem,
  type SignalsResponse,
} from "../../lib/api";

const PRESET_SYMBOLS = [
  "RELIANCE",
  "MIDCAP_STOCK_101",
  "HDFCBANK",
  "INFY",
  "TATAMOTORS",
];

export default function SignalsPage() {
  const [symbol, setSymbol] = useState("MIDCAP_STOCK_101");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2022-12-31");
  const [onlyEntries, setOnlyEntries] = useState(false);
  const [onlyExits, setOnlyExits] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [signalData, setSignalData] = useState<SignalsResponse | null>(null);

  // Universe screen state
  const [screenDate, setScreenDate] = useState("2020-06-25");
  const [screenLoading, setScreenLoading] = useState(false);
  const [screenResults, setScreenResults] = useState<{
    date: string;
    count: number;
    symbols: string[];
    survivorship_bias: boolean;
  } | null>(null);
  const [screenError, setScreenError] = useState<string | null>(null);

  const loadSignals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSignals(
        symbol,
        startDate || undefined,
        endDate || undefined
      );
      setSignalData(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load strategy signals"
      );
    } finally {
      setLoading(false);
    }
  }, [symbol, startDate, endDate]);

  useEffect(() => {
    loadSignals();
  }, [loadSignals]);

  const handleScreenUniverse = async () => {
    if (!screenDate) return;
    setScreenLoading(true);
    setScreenError(null);
    try {
      const res = await screenUniverse(screenDate);
      setScreenResults(res);
    } catch (err) {
      setScreenError(
        err instanceof Error ? err.message : "Failed to screen universe"
      );
    } finally {
      setScreenLoading(false);
    }
  };

  const filteredSignals = useMemo(() => {
    if (!signalData?.signals) return [];
    return signalData.signals.filter((item: SignalItem) => {
      if (onlyEntries && !item.entry) return false;
      if (onlyExits && !item.exit) return false;
      return true;
    });
  }, [signalData, onlyEntries, onlyExits]);

  const totalEntries = useMemo(() => {
    return (
      signalData?.signals.reduce(
        (acc: number, curr: SignalItem) => acc + (curr.entry ? 1 : 0),
        0
      ) ?? 0
    );
  }, [signalData]);

  const totalExits = useMemo(() => {
    return (
      signalData?.signals.reduce(
        (acc: number, curr: SignalItem) => acc + (curr.exit ? 1 : 0),
        0
      ) ?? 0
    );
  }, [signalData]);

  return (
    <div className="space-y-6">
      {/* Title & Overview */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Trading Signals & Strategy Rules
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Deterministic rule-based entry and exit signals evaluated on bar T
            for execution on session T+1 at the Open price.
          </p>
        </div>
      </div>

      {/* Strategy Rules Reference Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
          <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
            REQ-3.1 Market Regime
          </div>
          <div className="text-sm font-medium mt-1 text-slate-900 dark:text-slate-100">
            NIFTY &gt; EMA 50 &amp; 200
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            0 trades taken if False
          </div>
        </div>

        <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
          <div className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">
            REQ-3.2 Trend Filter
          </div>
          <div className="text-sm font-medium mt-1 text-slate-900 dark:text-slate-100">
            20 &gt; 50 &gt; 150 &gt; 200
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Strict ascending stack
          </div>
        </div>

        <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
          <div className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
            REQ-3.3 Price Filter
          </div>
          <div className="text-sm font-medium mt-1 text-slate-900 dark:text-slate-100">
            Close &gt; 0.85 × 52W High
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Within 15% of 52W high
          </div>
        </div>

        <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
          <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
            REQ-3.4 Entry Trigger
          </div>
          <div className="text-sm font-medium mt-1 text-slate-900 dark:text-slate-100">
            Close(T) &gt; EMA20
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Close(T-1) &lt; EMA20(T-1)
          </div>
        </div>

        <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
          <div className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
            REQ-3.5 Exit Trigger
          </div>
          <div className="text-sm font-medium mt-1 text-slate-900 dark:text-slate-100">
            Close(T) &lt; EMA20
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Execution on T+1 open
          </div>
        </div>
      </div>

      {/* Universe Screening Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <span>🔍</span> Universe Screen (NSE 101–750)
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">
              Evaluation Date:
            </label>
            <input
              type="date"
              value={screenDate}
              onChange={(e) => setScreenDate(e.target.value)}
              data-testid="screen-date-input"
              className="text-xs px-2.5 py-1.5 border border-slate-300 dark:border-slate-700 rounded bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleScreenUniverse}
            disabled={screenLoading || !screenDate}
            data-testid="screen-button"
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded text-xs font-medium transition-colors"
          >
            {screenLoading ? "Screening..." : "Screen for Entry Signals"}
          </button>
        </div>

        {screenError && (
          <div className="mt-3 text-xs text-rose-600 dark:text-rose-400">
            {screenError}
          </div>
        )}

        {screenResults && (
          <div
            className="mt-3.5 p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700 flex flex-wrap items-center justify-between gap-3 text-xs"
            data-testid="screen-results-card"
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Date: {screenResults.date}
              </span>
              <span className="text-slate-400">•</span>
              <span className="text-slate-600 dark:text-slate-400">
                Active Signals:{" "}
                <strong className="text-slate-900 dark:text-slate-100">
                  {screenResults.count}
                </strong>
              </span>
              {screenResults.survivorship_bias && (
                <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 text-[11px] font-semibold">
                  Survivorship Bias (Fallback Universe)
                </span>
              )}
            </div>

            <div
              className="flex items-center gap-1.5 flex-wrap"
              data-testid="screened-symbols-list"
            >
              {screenResults.symbols.length > 0 ? (
                screenResults.symbols.map((sym) => (
                  <button
                    key={sym}
                    onClick={() => setSymbol(sym)}
                    className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 font-mono font-medium hover:bg-emerald-200 transition-colors"
                    title={`Click to load signals for ${sym}`}
                  >
                    {sym}
                  </button>
                ))
              ) : (
                <span className="text-slate-500 italic">
                  No symbols triggered entry signals on this date
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Symbol Inspection Filters */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Symbol:
              </label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                data-testid="signal-symbol-select"
                className="text-xs px-2.5 py-1.5 border border-slate-300 dark:border-slate-700 rounded bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-mono font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {PRESET_SYMBOLS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Start:
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                data-testid="signal-start-date"
                className="text-xs px-2 py-1.5 border border-slate-300 dark:border-slate-700 rounded bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                End:
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                data-testid="signal-end-date"
                className="text-xs px-2 py-1.5 border border-slate-300 dark:border-slate-700 rounded bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-1.5 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={onlyEntries}
                onChange={(e) => {
                  setOnlyEntries(e.target.checked);
                  if (e.target.checked) setOnlyExits(false);
                }}
                data-testid="only-entries-toggle"
                className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5"
              />
              <span>Only Entries</span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={onlyExits}
                onChange={(e) => {
                  setOnlyExits(e.target.checked);
                  if (e.target.checked) setOnlyEntries(false);
                }}
                data-testid="only-exits-toggle"
                className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 h-3.5 w-3.5"
              />
              <span>Only Exits</span>
            </label>
          </div>
        </div>
      </div>

      {/* Signals Table Card */}
      <div
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm"
        data-testid="signals-table-card"
      >
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-2">
            <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">
              Signal Evaluations for {symbol}
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              {filteredSignals.length} bars
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 text-xs font-medium">
              Entries: {totalEntries}
            </span>
            <span className="px-2 py-0.5 rounded bg-rose-100 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 text-xs font-medium">
              Exits: {totalExits}
            </span>
          </div>
        </div>

        {error && (
          <div className="p-6 text-center text-sm text-rose-600 dark:text-rose-400">
            {error}
          </div>
        )}

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500 animate-pulse">
            Computing technical indicators and strategy signals...
          </div>
        ) : filteredSignals.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No signal rows match current criteria.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table
              className="w-full text-left border-collapse text-xs"
              data-testid="signals-table"
            >
              <thead className="bg-slate-50 dark:bg-slate-800/80 sticky top-0 z-10 border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Close</th>
                  <th className="py-2.5 px-3">Adj Close</th>
                  <th className="py-2.5 px-3 text-center">Signal Action</th>
                  <th className="py-2.5 px-3 text-center">Regime Filter</th>
                  <th className="py-2.5 px-3 text-center">Trend Stack</th>
                  <th className="py-2.5 px-3 text-center">52W High</th>
                  <th className="py-2.5 px-3 text-center">EMA20 Cross</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                {filteredSignals.map((item: SignalItem) => (
                  <tr
                    key={item.date}
                    data-testid="signal-row"
                    className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors ${
                      item.entry
                        ? "bg-emerald-50/40 dark:bg-emerald-950/20"
                        : item.exit
                        ? "bg-rose-50/30 dark:bg-rose-950/20"
                        : ""
                    }`}
                  >
                    <td className="py-2 px-3 font-semibold text-slate-900 dark:text-slate-100">
                      {item.date}
                    </td>
                    <td className="py-2 px-3">{item.close.toFixed(2)}</td>
                    <td className="py-2 px-3">{item.adj_close.toFixed(2)}</td>
                    <td className="py-2 px-3 text-center font-sans">
                      {item.entry ? (
                        <span
                          data-testid="entry-badge"
                          className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"
                        >
                          BUY / ENTRY
                        </span>
                      ) : item.exit ? (
                        <span
                          data-testid="exit-badge"
                          className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700"
                        >
                          SELL / EXIT
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">
                          HOLD
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {item.regime_ok ? (
                        <span className="text-emerald-600 font-bold">✓</span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">✗</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {item.trend_ok ? (
                        <span className="text-emerald-600 font-bold">✓</span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">✗</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {item.near_52w_high ? (
                        <span className="text-emerald-600 font-bold">✓</span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">✗</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {item.crossover ? (
                        <span className="text-emerald-600 font-bold">✓</span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">✗</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

