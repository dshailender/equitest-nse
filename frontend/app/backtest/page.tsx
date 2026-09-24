"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  type BacktestConfig,
  type BacktestStatusResponse,
  type EquityPoint,
  fetchBacktestEquity,
  fetchBacktestRuns,
  fetchBacktestStatus,
  fetchBacktestTrades,
  runBacktest,
  type TradeItem,
} from "../../lib/api";

export default function BacktestPage() {
  // Form State
  const [startDate, setStartDate] = useState<string>("2020-06-01");
  const [endDate, setEndDate] = useState<string>("2022-04-29");
  const [corpus, setCorpus] = useState<string>("500000");
  const [riskPct, setRiskPct] = useState<string>("2");
  const [slPct, setSlPct] = useState<string>("7");
  const [ema20, setEma20] = useState<string>("20");
  const [ema50, setEma50] = useState<string>("50");
  const [ema150, setEma150] = useState<string>("150");
  const [ema200, setEma200] = useState<string>("200");

  // Execution & Polling State
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>("idle"); // idle, pending, running, completed, failed
  const [statusData, setStatusData] = useState<BacktestStatusResponse | null>(null);
  const [trades, setTrades] = useState<TradeItem[]>([]);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [pastRuns, setPastRuns] = useState<BacktestStatusResponse[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Table Filter State
  const [searchSymbol, setSearchSymbol] = useState<string>("");
  const [exitReasonFilter, setExitReasonFilter] = useState<string>("all");

  // Load Past Runs on Mount
  const loadPastRuns = useCallback(async () => {
    try {
      const runs = await fetchBacktestRuns();
      setPastRuns(runs);
    } catch {
      // Ignored if API is not yet seeded
    }
  }, []);

  useEffect(() => {
    loadPastRuns();
  }, [loadPastRuns]);

  // Load specific run results
  const loadRunDetails = useCallback(async (runId: string) => {
    try {
      const statusRes = await fetchBacktestStatus(runId);
      setStatusData(statusRes);
      setRunStatus(statusRes.status);
      setActiveRunId(runId);

      if (statusRes.status === "completed") {
        const [tradesRes, equityRes] = await Promise.all([
          fetchBacktestTrades(runId),
          fetchBacktestEquity(runId),
        ]);
        setTrades(tradesRes.trades);
        setEquityCurve(equityRes.equity_curve);
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load run details"
      );
    }
  }, []);

  // Polling Effect
  useEffect(() => {
    if (!activeRunId || (runStatus !== "pending" && runStatus !== "running")) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const currentStatus = await fetchBacktestStatus(activeRunId);
        setStatusData(currentStatus);
        setRunStatus(currentStatus.status);

        if (currentStatus.status === "completed") {
          clearInterval(interval);
          const [tradesRes, equityRes] = await Promise.all([
            fetchBacktestTrades(activeRunId),
            fetchBacktestEquity(activeRunId),
          ]);
          setTrades(tradesRes.trades);
          setEquityCurve(equityRes.equity_curve);
          loadPastRuns();
        } else if (currentStatus.status === "failed") {
          clearInterval(interval);
          setErrorMessage(
            currentStatus.error_message || "Backtest execution failed"
          );
        }
      } catch (err: unknown) {
        clearInterval(interval);
        setErrorMessage(
          err instanceof Error ? err.message : "Polling backtest status failed"
        );
        setRunStatus("failed");
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeRunId, runStatus, loadPastRuns]);

  // Submit Run Handler
  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setRunStatus("pending");

    const parsedCorpus = parseFloat(corpus) || 500000.0;
    const parsedRisk = (parseFloat(riskPct) || 2.0) / 100.0;
    const parsedSl = (parseFloat(slPct) || 7.0) / 100.0;

    const config: BacktestConfig = {
      corpus: parsedCorpus,
      risk_pct: parsedRisk,
      stop_loss_pct: parsedSl,
      lot_size: 1,
      cost_bps: 10.0,
      ema_spans: [
        parseInt(ema20) || 20,
        parseInt(ema50) || 50,
        parseInt(ema150) || 150,
        parseInt(ema200) || 200,
      ],
      regime_spans: [50, 200],
      high_52w_factor: 0.85,
      high_52w_lookback: 252,
      allow_crossover_equal: false,
      ranking_rule: "momentum",
      universe_start_rank: 101,
      universe_end_rank: 750,
    };

    try {
      const createRes = await runBacktest({
        start: startDate || null,
        end: endDate || null,
        config,
      });
      setActiveRunId(createRes.run_id);
      setRunStatus("running");
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to trigger backtest"
      );
      setRunStatus("failed");
    }
  };

  // Filtered Trades
  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      const matchesSymbol =
        !searchSymbol ||
        t.symbol.toUpperCase().includes(searchSymbol.trim().toUpperCase());
      const matchesReason =
        exitReasonFilter === "all" || t.exit_reason === exitReasonFilter;
      return matchesSymbol && matchesReason;
    });
  }, [trades, searchSymbol, exitReasonFilter]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Backtest Simulation Engine
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Execute event-driven simulations with next-day open execution, 7% stop
          loss, 2% dynamic risk sizing, and portfolio capital constraints (Phase
          5).
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Form & History */}
        <div className="lg:col-span-1 space-y-6">
          {/* Config Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Simulation Parameters
            </h2>

            <form onSubmit={handleRun} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    data-testid="input-start-date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full text-xs px-3 py-2 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    data-testid="input-end-date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full text-xs px-3 py-2 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                  Starting Corpus (₹)
                </label>
                <input
                  type="number"
                  data-testid="input-corpus"
                  value={corpus}
                  onChange={(e) => setCorpus(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Risk per Trade (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    data-testid="input-risk"
                    value={riskPct}
                    onChange={(e) => setRiskPct(e.target.value)}
                    className="w-full text-xs px-3 py-2 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Stop Loss (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    data-testid="input-sl"
                    value={slPct}
                    onChange={(e) => setSlPct(e.target.value)}
                    className="w-full text-xs px-3 py-2 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                  Trend EMA Spans
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  <input
                    type="number"
                    value={ema20}
                    onChange={(e) => setEma20(e.target.value)}
                    className="text-xs px-2 py-1.5 text-center border rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    placeholder="20"
                  />
                  <input
                    type="number"
                    value={ema50}
                    onChange={(e) => setEma50(e.target.value)}
                    className="text-xs px-2 py-1.5 text-center border rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    placeholder="50"
                  />
                  <input
                    type="number"
                    value={ema150}
                    onChange={(e) => setEma150(e.target.value)}
                    className="text-xs px-2 py-1.5 text-center border rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    placeholder="150"
                  />
                  <input
                    type="number"
                    value={ema200}
                    onChange={(e) => setEma200(e.target.value)}
                    className="text-xs px-2 py-1.5 text-center border rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                    placeholder="200"
                  />
                </div>
              </div>

              <button
                type="submit"
                data-testid="btn-run-backtest"
                disabled={runStatus === "running" || runStatus === "pending"}
                className="w-full mt-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition-colors shadow-sm flex items-center justify-center space-x-2"
              >
                {runStatus === "running" || runStatus === "pending" ? (
                  <>
                    <span className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Running Simulation...</span>
                  </>
                ) : (
                  <span>Run Backtest</span>
                )}
              </button>
            </form>

            {errorMessage && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg text-xs text-red-600 dark:text-red-400">
                {errorMessage}
              </div>
            )}
          </div>

          {/* Past Runs Sidebar */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
              Run History
            </h3>
            {pastRuns.length === 0 ? (
              <p className="text-xs text-slate-400">No past runs recorded</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {pastRuns.map((r) => (
                  <button
                    key={r.run_id}
                    onClick={() => loadRunDetails(r.run_id)}
                    className={`w-full text-left p-2.5 rounded-lg border text-xs transition-colors flex items-center justify-between ${
                      activeRunId === r.run_id
                        ? "border-blue-500 bg-blue-50/50 dark:bg-blue-950/30"
                        : "border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    }`}
                  >
                    <div>
                      <div className="font-mono text-slate-800 dark:text-slate-200">
                        {r.run_id}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {r.created_at.slice(0, 16).replace("T", " ")}
                      </div>
                    </div>
                    <div className="text-right">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          r.status === "completed"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400"
                            : r.status === "failed"
                              ? "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400"
                              : "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400"
                        }`}
                      >
                        {r.status}
                      </span>
                      {r.final_capital != null && (
                        <div className="text-[10px] font-semibold text-slate-600 dark:text-slate-300 mt-0.5">
                          ₹{r.final_capital.toLocaleString()}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Results & Analytics */}
        <div className="lg:col-span-2 space-y-6">
          {runStatus === "running" || runStatus === "pending" ? (
            <div className="h-64 flex flex-col items-center justify-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 text-center space-y-3">
              <div className="h-8 w-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <div className="font-semibold text-sm text-slate-800 dark:text-slate-200">
                Running Backtest Simulation...
              </div>
              <div className="text-xs text-slate-500 font-mono">
                Job ID: {activeRunId}
              </div>
            </div>
          ) : statusData && statusData.status === "completed" ? (
            <>
              {/* Summary KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
                  <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                    Final Capital
                  </span>
                  <div
                    data-testid="final-capital-value"
                    className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1"
                  >
                    ₹{(statusData.final_capital ?? 500000).toLocaleString(
                      undefined,
                      { minimumFractionDigits: 2, maximumFractionDigits: 2 }
                    )}
                  </div>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
                  <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                    Total Return
                  </span>
                  <div
                    data-testid="total-return-value"
                    className={`text-lg font-bold mt-1 ${
                      (statusData.total_return_pct ?? 0) >= 0
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {((statusData.total_return_pct ?? 0) * 100).toFixed(2)}%
                  </div>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
                  <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                    Total Trades
                  </span>
                  <div
                    data-testid="total-trades-value"
                    className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1"
                  >
                    {statusData.total_trades ?? 0}
                  </div>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
                  <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                    Win Rate
                  </span>
                  <div
                    data-testid="win-rate-value"
                    className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1"
                  >
                    {((statusData.win_rate ?? 0) * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Equity Curve Chart */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-4">
                  Portfolio Equity Curve (Mark-to-Market)
                </h3>
                <div
                  data-testid="equity-chart-container"
                  className="h-64 w-full"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityCurve}>
                      <defs>
                        <linearGradient
                          id="equityGrad"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor="#3b82f6"
                            stopOpacity={0.4}
                          />
                          <stop
                            offset="95%"
                            stopColor="#3b82f6"
                            stopOpacity={0.0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#e2e8f0"
                        opacity={0.5}
                      />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10 }}
                        tickFormatter={(d: string) => d.slice(5)}
                      />
                      <YAxis
                        domain={["auto", "auto"]}
                        tick={{ fontSize: 10 }}
                        tickFormatter={(v: number) => `₹${(v / 1000).toFixed(0)}k`}
                      />
                      <Tooltip
                        formatter={(val: number) => [
                          `₹${val.toLocaleString()}`,
                          "Equity",
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey="equity"
                        stroke="#2563eb"
                        strokeWidth={2}
                        fill="url(#equityGrad)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Trades Ledger Table */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Trade Ledger ({filteredTrades.length})
                  </h3>

                  <div className="flex items-center space-x-3">
                    <input
                      type="text"
                      placeholder="Filter symbol..."
                      value={searchSymbol}
                      onChange={(e) => setSearchSymbol(e.target.value)}
                      className="text-xs px-2.5 py-1.5 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 outline-none w-32"
                    />

                    <select
                      value={exitReasonFilter}
                      onChange={(e) => setExitReasonFilter(e.target.value)}
                      className="text-xs px-2.5 py-1.5 border rounded-lg border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 outline-none"
                    >
                      <option value="all">All Exits</option>
                      <option value="gap">Gap Down</option>
                      <option value="stop_loss">Stop Loss</option>
                      <option value="exit_signal">Exit Signal</option>
                    </select>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table
                    data-testid="trades-table"
                    className="w-full text-left text-xs"
                  >
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-medium">
                        <th className="py-2.5 px-3">Symbol</th>
                        <th className="py-2.5 px-3">Entry Date</th>
                        <th className="py-2.5 px-3">Entry Price</th>
                        <th className="py-2.5 px-3">Qty</th>
                        <th className="py-2.5 px-3">Exit Date</th>
                        <th className="py-2.5 px-3">Exit Price</th>
                        <th className="py-2.5 px-3 text-right">Net P&L</th>
                        <th className="py-2.5 px-3 text-right">Return</th>
                        <th className="py-2.5 px-3">Reason</th>
                        <th className="py-2.5 px-3 text-right">Days</th>
                        <th className="py-2.5 px-3 text-right">Costs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                      {filteredTrades.length === 0 ? (
                        <tr>
                          <td
                            colSpan={11}
                            className="py-6 text-center text-slate-400"
                          >
                            No trades match filter criteria
                          </td>
                        </tr>
                      ) : (
                        filteredTrades.map((t, idx) => (
                          <tr
                            key={`${t.symbol}-${t.entry_date}-${idx}`}
                            className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30"
                          >
                            <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-slate-100">
                              {t.symbol}
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                              {t.entry_date}
                            </td>
                            <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                              ₹{t.entry_price.toFixed(2)}
                            </td>
                            <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                              {t.qty}
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                              {t.exit_date}
                            </td>
                            <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                              ₹{t.exit_price.toFixed(2)}
                            </td>
                            <td
                              className={`py-2.5 px-3 text-right font-semibold ${
                                t.pnl >= 0
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-red-600 dark:text-red-400"
                              }`}
                            >
                              ₹{t.pnl.toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </td>
                            <td
                              className={`py-2.5 px-3 text-right font-medium ${
                                t.pnl_pct >= 0
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-red-600 dark:text-red-400"
                              }`}
                            >
                              {(t.pnl_pct * 100).toFixed(2)}%
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                  t.exit_reason === "gap"
                                    ? "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400"
                                    : t.exit_reason === "stop_loss"
                                      ? "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400"
                                      : "bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400"
                                }`}
                              >
                                {t.exit_reason === "gap"
                                  ? "Gap Down"
                                  : t.exit_reason === "stop_loss"
                                    ? "Stop Loss"
                                    : "Exit Signal"}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-600 dark:text-slate-400">
                              {t.days_held}
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-500">
                              ₹{t.costs.toFixed(2)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center bg-white dark:bg-slate-900 border border-dashed border-slate-300 dark:border-slate-800 rounded-xl p-8 text-center text-slate-400">
              <p className="text-sm">
                Configure parameters and click &quot;Run Backtest&quot; to begin
                simulation.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
