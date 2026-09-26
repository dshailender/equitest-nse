"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Download, Filter, RefreshCw, Search } from "lucide-react";
import {
  type BacktestStatusResponse,
  type CrossCheckPoint,
  fetchBacktestRuns,
  fetchCrossCheck,
  getCrossCheckDownloadUrl,
} from "../../lib/api";

const PRESET_SYMBOLS = [
  "BALKRISIND",
  "FEDERALBNK",
  "TATAELXSI",
  "AUBANK",
  "ASHOKLEY",
];

export default function ValidationPage() {
  const [runs, setRuns] = useState<BacktestStatusResponse[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("default");
  const [symbol, setSymbol] = useState<string>("BALKRISIND");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<CrossCheckPoint[]>([]);
  const [signalsOnly, setSignalsOnly] = useState<boolean>(false);

  // Load available past runs on mount
  useEffect(() => {
    async function loadRuns() {
      try {
        const pastRuns = await fetchBacktestRuns();
        setRuns(pastRuns);
      } catch {
        // Fallback to "default" run config
      }
    }
    loadRuns();
  }, []);

  const handleFetch = useCallback(
    async (targetRunId: string, targetSymbol: string) => {
      if (!targetSymbol.trim()) return;
      try {
        setLoading(true);
        setError(null);
        const res = await fetchCrossCheck(targetRunId || "default", targetSymbol.trim().toUpperCase());
        setRows(res.rows);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load cross-check data");
        setRows([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Auto-fetch on initial load
  useEffect(() => {
    handleFetch(selectedRunId, symbol);
  }, [handleFetch, selectedRunId, symbol]);

  const filteredRows = useMemo(() => {
    if (!signalsOnly) return rows;
    return rows.filter((r) => r.entry || r.exit);
  }, [rows, signalsOnly]);

  const stats = useMemo(() => {
    const totalEntries = rows.filter((r) => r.entry).length;
    const totalExits = rows.filter((r) => r.exit).length;
    const firstDate = rows.length > 0 ? rows[0].date : "-";
    const lastDate = rows.length > 0 ? rows[rows.length - 1].date : "-";
    return { totalEntries, totalExits, firstDate, lastDate, count: rows.length };
  }, [rows]);

  const handleDownload = () => {
    const downloadUrl = getCrossCheckDownloadUrl(selectedRunId, symbol);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", `${symbol}_cross_check_${selectedRunId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6" data-testid="validation-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            TradingView Cross-Check Verification
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Generate and export aligned OHLCV, 4 EMAs, 52W rolling high, and entry/exit signal series for visual diff against charting platforms.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownload}
            disabled={rows.length === 0}
            data-testid="btn-download-tv"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white text-sm font-medium shadow-sm transition-colors"
          >
            <Download className="w-4 h-4" />
            Download for TradingView Diff
          </button>
        </div>
      </div>

      {/* Control Form */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-end">
          {/* Run Selection */}
          <div>
            <label htmlFor="run-select" className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
              Backtest Run Context
            </label>
            <select
              id="run-select"
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              data-testid="run-select"
              className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="default">Default Baseline Strategy Config</option>
              {runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_id} ({r.status}) {r.start_date ? `[${r.start_date} → ${r.end_date}]` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Symbol Selection */}
          <div>
            <label htmlFor="symbol-input" className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
              Symbol Ticker
            </label>
            <div className="relative">
              <input
                id="symbol-input"
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                data-testid="symbol-input"
                placeholder="e.g. BALKRISIND, FEDERALBNK"
                className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg uppercase tracking-wide focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                aria-label="Refresh cross-check data"
                onClick={() => handleFetch(selectedRunId, symbol)}
                data-testid="btn-fetch-cross-check"
                className="absolute right-1.5 top-1.5 p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {/* Quick Select Buttons */}
          <div className="flex flex-wrap items-center gap-1.5">
            {PRESET_SYMBOLS.map((sym) => (
              <button
                key={sym}
                type="button"
                onClick={() => {
                  setSymbol(sym);
                  handleFetch(selectedRunId, sym);
                }}
                className={`px-2.5 py-1.5 text-xs font-semibold rounded border transition-colors ${
                  symbol === sym
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                }`}
              >
                {sym}
              </button>
            ))}
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-sm">
          <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300 select-none">
            <input
              type="checkbox"
              checked={signalsOnly}
              onChange={(e) => setSignalsOnly(e.target.checked)}
              data-testid="toggle-signals-only"
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="font-medium text-xs">Show only sessions with Entry / Exit signals</span>
          </label>

          <span className="text-xs text-slate-600 dark:text-slate-400">
            Showing <strong className="text-slate-900 dark:text-slate-100">{filteredRows.length}</strong> of {stats.count} trading sessions
          </span>
        </div>
      </div>

      {/* Summary Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase">Trading Sessions</span>
          <p className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1" data-testid="stat-sessions">
            {stats.count}
          </p>
          <span className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 block">{stats.firstDate} → {stats.lastDate}</span>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase">Entry Signals</span>
          <p className="text-xl font-bold text-emerald-600 mt-1" data-testid="stat-entries">
            {stats.totalEntries}
          </p>
          <span className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 block">Cross above EMA-20</span>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase">Exit Signals</span>
          <p className="text-xl font-bold text-rose-600 mt-1" data-testid="stat-exits">
            {stats.totalExits}
          </p>
          <span className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 block">Close below EMA-20</span>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase">Validation Context</span>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mt-1 truncate" title={selectedRunId}>
            {selectedRunId === "default" ? "Baseline" : selectedRunId}
          </p>
          <span className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 block">{symbol} Series</span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
          <strong>Error loading cross-check data:</strong> {error}
        </div>
      )}

      {/* Cross-Check Data Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">
              Cross-Check Series Table
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono break-all">
              date,close,ema_20,ema_50,ema_150,ema_200,high_52w,entry,exit
            </span>
          </div>
        </div>

        <div
          className="overflow-x-auto max-h-[560px] overflow-y-auto"
          tabIndex={0}
          role="region"
          aria-label="TradingView cross-check data table"
        >
          <table className="w-full text-left border-collapse text-xs" data-testid="table-cross-check">
            <thead className="bg-slate-50 dark:bg-slate-800/80 sticky top-0 z-10 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="py-2.5 px-4 font-semibold text-slate-700 dark:text-slate-300">Date</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-right">Close (₹)</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-right">EMA 20</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-right">EMA 50</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-right">EMA 150</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-right">EMA 200</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-right">52W High</th>
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-center">Entry</th>
                <th className="py-2.5 px-4 font-semibold text-slate-700 dark:text-slate-300 text-center">Exit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-600 dark:text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-500" />
                    Computing indicators and signals...
                  </td>
                </tr>
              ) : filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-600 dark:text-slate-400 font-sans">
                    No records found matching filters.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr
                    key={row.date}
                    data-testid="cross-check-row"
                    className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors ${
                      row.entry
                        ? "bg-emerald-50/40 dark:bg-emerald-950/20"
                        : row.exit
                        ? "bg-rose-50/30 dark:bg-rose-950/10"
                        : ""
                    }`}
                  >
                    <td className="py-2 px-4 text-slate-900 dark:text-slate-100 font-medium">
                      {row.date}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-800 dark:text-slate-200">
                      ₹{row.close.toFixed(2)}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-400">
                      {row.ema_20 != null ? row.ema_20.toFixed(2) : <span className="text-slate-300 dark:text-slate-600">-</span>}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-400">
                      {row.ema_50 != null ? row.ema_50.toFixed(2) : <span className="text-slate-300 dark:text-slate-600">-</span>}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-400">
                      {row.ema_150 != null ? row.ema_150.toFixed(2) : <span className="text-slate-300 dark:text-slate-600">-</span>}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-400">
                      {row.ema_200 != null ? row.ema_200.toFixed(2) : <span className="text-slate-300 dark:text-slate-600">-</span>}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-400">
                      {row.high_52w != null ? row.high_52w.toFixed(2) : <span className="text-slate-300 dark:text-slate-600">-</span>}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {row.entry ? (
                        <span
                          data-testid="badge-entry"
                          className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-700 text-white uppercase tracking-wider"
                        >
                          ENTRY
                        </span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">-</span>
                      )}
                    </td>
                    <td className="py-2 px-4 text-center">
                      {row.exit ? (
                        <span
                          data-testid="badge-exit"
                          className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white uppercase tracking-wider"
                        >
                          EXIT
                        </span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">-</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
