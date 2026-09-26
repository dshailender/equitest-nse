"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchBacktestEquity,
  fetchBacktestTrades,
  fetchReportMonthly,
  fetchReportSummary,
  getReportExportUrl,
  type MonthlyReturnRow,
  type PerformanceMetrics,
  type ReportSummaryResponse,
} from "@/lib/api";
import { AuditPanel } from "@/components/AuditPanel";
import { ExportButton } from "@/components/ExportButton";


const MONTH_COLS = [
  { key: "jan", label: "Jan" },
  { key: "feb", label: "Feb" },
  { key: "mar", label: "Mar" },
  { key: "apr", label: "Apr" },
  { key: "may", label: "May" },
  { key: "jun", label: "Jun" },
  { key: "jul", label: "Jul" },
  { key: "aug", label: "Aug" },
  { key: "sep", label: "Sep" },
  { key: "oct", label: "Oct" },
  { key: "nov", label: "Nov" },
  { key: "dec", label: "Dec" },
] as const;

function formatCurrency(val: number): string {
  const isNeg = val < 0;
  const abs = Math.abs(val);
  return `${isNeg ? "-" : ""}₹${abs.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function getCellColorClass(val: number | null | undefined): string {
  if (val === null || val === undefined) {
    return "bg-slate-100/50 dark:bg-slate-800/20 text-slate-600 dark:text-slate-400";
  }
  if (val === 0) {
    return "bg-slate-50 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400";
  }
  if (val > 0) {
    if (val >= 0.05) return "bg-emerald-700 text-white font-semibold";
    if (val >= 0.02) return "bg-emerald-800 text-white font-medium";
    if (val >= 0.01) return "bg-emerald-200 text-emerald-950 dark:bg-emerald-900/60 dark:text-emerald-200";
    return "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300";
  } else {
    if (val <= -0.05) return "bg-rose-700 text-white font-semibold";
    if (val <= -0.02) return "bg-rose-800 text-white font-medium";
    if (val <= -0.01) return "bg-rose-200 text-rose-950 dark:bg-rose-900/60 dark:text-rose-200";
    return "bg-rose-100 text-rose-900 dark:bg-rose-950/40 dark:text-rose-300";
  }
}

export default function ReportDetailPage({
  params,
}: {
  params: { runId: string };
}) {
  const { runId } = params;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ReportSummaryResponse | null>(null);
  const [monthly, setMonthly] = useState<MonthlyReturnRow[]>([]);
  const [equityCurve, setEquityCurve] = useState<
    {
      date: string;
      drawdown_pct: number;
      equity: number;
      benchmark_equity?: number | null;
    }[]
  >([]);
  const [trades, setTrades] = useState<{ pnl_pct: number; pnl: number }[]>([]);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [sumRes, monRes, eqRes, trRes] = await Promise.all([
          fetchReportSummary(runId),
          fetchReportMonthly(runId),
          fetchBacktestEquity(runId).catch(() => ({ equity_curve: [] })),
          fetchBacktestTrades(runId).catch(() => ({ trades: [] })),
        ]);

        if (!isMounted) return;
        setSummary(sumRes);
        setMonthly(monRes.years || []);

        const mappedEq = (eqRes.equity_curve || []).map((pt) => ({
          date: pt.date,
          drawdown_pct:
            pt.drawdown_pct != null ? -Math.abs(pt.drawdown_pct * 100) : 0,
          equity: pt.equity,
          benchmark_equity:
            pt.benchmark_equity != null ? pt.benchmark_equity : null,
        }));
        setEquityCurve(mappedEq);

        const mappedTr = (trRes.trades || []).map((t) => ({
          pnl_pct: t.pnl_pct != null ? t.pnl_pct * 100 : 0,
          pnl: t.pnl,
        }));
        setTrades(mappedTr);
      } catch (err: unknown) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Failed to load report");
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [runId]);

  // Trade PnL % Distribution Histogram Bins
  const histogramData = useMemo(() => {
    if (!trades || trades.length === 0) {
      return [
        { bin: "<-10%", count: 0 },
        { bin: "-10% to -5%", count: 0 },
        { bin: "-5% to 0%", count: 0 },
        { bin: "0% to +5%", count: 0 },
        { bin: "+5% to +10%", count: 0 },
        { bin: ">+10%", count: 0 },
      ];
    }

    const bins = {
      "<-10%": 0,
      "-10% to -5%": 0,
      "-5% to 0%": 0,
      "0% to +5%": 0,
      "+5% to +10%": 0,
      ">+10%": 0,
    };

    trades.forEach((t) => {
      const p = t.pnl_pct;
      if (p < -10) bins["<-10%"]++;
      else if (p < -5) bins["-10% to -5%"]++;
      else if (p <= 0) bins["-5% to 0%"]++;
      else if (p <= 5) bins["0% to +5%"]++;
      else if (p <= 10) bins["+5% to +10%"]++;
      else bins[">+10%"]++;
    });

    return Object.entries(bins).map(([bin, count]) => ({ bin, count }));
  }, [trades]);

  const handleDownload = (format: "csv" | "xlsx" | "zip") => {
    const url = getReportExportUrl(runId, format);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${runId}_${format === "csv" ? "trades.csv" : format === "xlsx" ? "report.xlsx" : "report.zip"}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-500 font-medium">
          Loading report & analytics for {runId}...
        </p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-xl max-w-xl mx-auto my-12 text-center space-y-3">
        <h1 className="text-base font-semibold text-red-800 dark:text-red-300">
          Failed to Load Report
        </h1>
        <p className="text-xs text-red-800 dark:text-red-200">{error || "Report not found"}</p>
        <Link
          href="/backtest"
          className="inline-block mt-2 px-4 py-2 bg-slate-800 text-white rounded-lg text-xs hover:bg-slate-700"
        >
          Return to Backtest Engine
        </Link>
      </div>
    );
  }

  const m: PerformanceMetrics = summary.metrics;

  return (
    <div className="space-y-8 pb-12">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs text-slate-600 dark:text-slate-400 mb-1">
            <Link href="/backtest" className="hover:text-blue-600 transition-colors">
              Backtest
            </Link>
            <span>/</span>
            <span className="font-mono text-slate-700 dark:text-slate-300">
              {summary.run_id}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Strategy Performance Report
          </h1>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Generated on {new Date(summary.created_at).toLocaleString()} • Status:{" "}
            <span className="inline-block px-1.5 py-0.5 rounded text-[11px] font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
              {summary.status}
            </span>
          </p>
        </div>

        {/* Export Toolbar */}
        <div className="flex items-center space-x-2">
          <ExportButton format="pdf" runId={summary.run_id} />
          <button
            onClick={() => handleDownload("csv")}
            data-testid="btn-export-csv"
            className="px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center space-x-1.5"
          >
            <span>📥</span>
            <span>Export CSV</span>
          </button>
          <button
            onClick={() => handleDownload("xlsx")}
            data-testid="btn-export-xlsx"
            className="px-3.5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center space-x-1.5"
          >
            <span>📊</span>
            <span>Export Excel</span>
          </button>
          <button
            onClick={() => handleDownload("zip")}
            data-testid="btn-export-zip"
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center space-x-1.5"
          >
            <span>📦</span>
            <span>ZIP Bundle</span>
          </button>
        </div>
      </div>

      {/* Core KPI Cards Grid */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-3">
          Core Performance KPIs
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Final Capital
            </span>
            <div
              data-testid="metric-final-capital"
              className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {formatCurrency(m.final_capital)}
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              Start: {formatCurrency(m.initial_capital)}
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Total Return
            </span>
            <div
              data-testid="metric-total-return"
              className={`text-lg font-bold mt-1 ${
                m.total_return_pct >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
              }`}
            >
              {(m.total_return_pct * 100).toFixed(2)}%
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              Net: {formatCurrency(m.net_profit)}
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Total Trades
            </span>
            <div
              data-testid="metric-total-trades"
              className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {m.total_trades}
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              {m.win_trades}W / {m.loss_trades}L
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Win Rate
            </span>
            <div
              data-testid="metric-win-rate"
              className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {(m.win_rate * 100).toFixed(2)}%
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">Closed round-trips</span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Avg Profit
            </span>
            <div
              data-testid="metric-avg-profit"
              className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1"
            >
              {formatCurrency(m.avg_profit)}
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">Per winning trade</span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
            <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Avg Loss
            </span>
            <div
              data-testid="metric-avg-loss"
              className="text-lg font-bold text-rose-600 dark:text-rose-400 mt-1"
            >
              {formatCurrency(m.avg_loss)}
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">Per losing trade</span>
          </div>
        </div>
      </div>

      {/* Advanced Risk & Return Metrics */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-3">
          Advanced Risk & Return Metrics
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              CAGR
            </span>
            <div
              data-testid="metric-cagr"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {(m.cagr * 100).toFixed(2)}%
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Max Drawdown
            </span>
            <div
              data-testid="metric-max-drawdown"
              className="text-base font-bold text-rose-600 dark:text-rose-400 mt-1"
            >
              {(m.max_drawdown_pct * 100).toFixed(2)}%
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Sharpe (rf=0)
            </span>
            <div
              data-testid="metric-sharpe"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {m.sharpe_ratio.toFixed(4)}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Sortino
            </span>
            <div
              data-testid="metric-sortino"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {m.sortino_ratio.toFixed(4)}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Calmar
            </span>
            <div
              data-testid="metric-calmar"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {m.calmar_ratio.toFixed(4)}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Profit Factor
            </span>
            <div
              data-testid="metric-profit-factor"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {m.profit_factor === Infinity ? "∞" : m.profit_factor.toFixed(2)}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Expectancy
            </span>
            <div
              data-testid="metric-expectancy"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {formatCurrency(m.expectancy)}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Avg Days Held
            </span>
            <div
              data-testid="metric-avg-days-held"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {m.avg_days_held.toFixed(1)}d
            </div>
          </div>
        </div>
      </div>

      {/* Benchmark Comparison & Relative Analytics (AUD-H-001) */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-3">
          Benchmark Comparison & Relative Analytics (NIFTY 50)
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Benchmark Return
            </span>
            <div
              data-testid="metric-benchmark-return"
              className={`text-base font-bold mt-1 ${
                (m.benchmark_return ?? 0) >= 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-rose-600 dark:text-rose-400"
              }`}
            >
              {((m.benchmark_return ?? 0) * 100).toFixed(2)}%
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              NIFTY 50 Buy &amp; Hold
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Benchmark CAGR
            </span>
            <div
              data-testid="metric-benchmark-cagr"
              className={`text-base font-bold mt-1 ${
                (m.benchmark_cagr ?? 0) >= 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-rose-600 dark:text-rose-400"
              }`}
            >
              {((m.benchmark_cagr ?? 0) * 100).toFixed(2)}%
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              Annualized geometric
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Strategy Alpha
            </span>
            <div
              data-testid="metric-alpha"
              className={`text-base font-bold mt-1 ${
                (m.alpha ?? 0) >= 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-rose-600 dark:text-rose-400"
              }`}
            >
              {((m.alpha ?? 0) * 100).toFixed(2)}%
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              Annualized Jensen&apos;s alpha
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Strategy Beta
            </span>
            <div
              data-testid="metric-beta"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {(m.beta ?? 0).toFixed(2)}
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              Sensitivity to NIFTY
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-sm">
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Information Ratio
            </span>
            <div
              data-testid="metric-information-ratio"
              className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1"
            >
              {(m.information_ratio ?? 0).toFixed(2)}
            </div>
            <span className="text-[10px] text-slate-600 dark:text-slate-400">
              Active return / Tracking error
            </span>
          </div>
        </div>
      </div>

      {/* Equity Curve vs NIFTY Benchmark Overlaid Chart (AUD-H-001) */}
      <div
        data-testid="chart-equity-curve"
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Equity Curve vs NIFTY 50 Benchmark
            </h3>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Portfolio equity progression overlaid with buy-and-hold NIFTY 50 benchmark
            </p>
          </div>
          <div className="flex items-center space-x-4 text-xs font-medium">
            <div className="flex items-center space-x-1.5">
              <span className="inline-block w-3 h-0.5 bg-blue-600"></span>
              <span className="text-slate-700 dark:text-slate-300">Strategy</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="inline-block w-3 h-0.5 bg-amber-500 border-b border-dashed border-amber-500"></span>
              <span className="text-slate-700 dark:text-slate-300">NIFTY 50 Benchmark</span>
            </div>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="strategyEquityFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                tickFormatter={(val) => (typeof val === "string" ? val.slice(0, 7) : val)}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
                domain={["auto", "auto"]}
              />
              <Tooltip
                formatter={(val: number, name: string) => [
                  formatCurrency(val),
                  name === "equity" ? "Strategy Equity" : "NIFTY 50 Benchmark",
                ]}
                labelFormatter={(lbl) => `Date: ${lbl}`}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="equity"
                name="Strategy Equity"
                stroke="#2563eb"
                fill="url(#strategyEquityFill)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="benchmark_equity"
                name="NIFTY 50 Benchmark"
                stroke="#f59e0b"
                strokeDasharray="4 4"
                fill="none"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Grid: Underwater Drawdown Curve & Trade Distribution Histogram */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Underwater Drawdown Chart */}
        <div
          data-testid="chart-drawdown"
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Underwater Drawdown Curve
              </h3>
              <p className="text-[11px] text-slate-600 dark:text-slate-400">
                Daily peak-to-trough equity decline percentage
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-rose-600 dark:text-rose-400">
              Max: -{(m.max_drawdown_pct * 100).toFixed(2)}%
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityCurve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="drawdownFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(val) => val.slice(0, 7)}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickFormatter={(val) => `${val}%`}
                  domain={["auto", 0]}
                />
                <Tooltip
                  formatter={(val: number) => [`${val.toFixed(2)}%`, "Drawdown"]}
                  labelFormatter={(lbl) => `Date: ${lbl}`}
                />
                <Area
                  type="monotone"
                  dataKey="drawdown_pct"
                  stroke="#e11d48"
                  fill="url(#drawdownFill)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Trade PnL % Distribution Histogram */}
        <div
          data-testid="chart-trade-distribution"
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Trade Return Distribution
              </h3>
              <p className="text-[11px] text-slate-600 dark:text-slate-400">
                Frequency histogram of closed trade PnL percentages
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-slate-600 dark:text-slate-300">
              {m.total_trades} trades
            </span>
          </div>

          <div data-testid="chart-histogram" className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={histogramData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip
                  formatter={(val: number) => [val, "Trades Count"]}
                  labelFormatter={(lbl) => `PnL Bin: ${lbl}`}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Month x Year Returns Matrix Heatmap Table */}
      <div
        data-testid="table-monthly-returns"
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm overflow-hidden"
      >
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Monthly Returns Matrix & Heatmap
          </h3>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            Compounded month-by-month and year-to-date performance (%)
          </p>
        </div>

        <div
          className="overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Monthly returns matrix"
        >
          <table className="w-full text-center border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                <th className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-left">
                  Year
                </th>
                {MONTH_COLS.map((col) => (
                  <th key={col.key} className="py-2.5 px-2 font-medium text-slate-600 dark:text-slate-400">
                    {col.label}
                  </th>
                ))}
                <th className="py-2.5 px-3 font-bold text-slate-800 dark:text-slate-200">
                  Total
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {monthly.length === 0 ? (
                <tr>
                  <td colSpan={14} className="py-8 text-slate-600 dark:text-slate-400 text-center font-sans">
                    No monthly performance data available
                  </td>
                </tr>
              ) : (
                monthly.map((row) => (
                  <tr key={row.year} className="hover:bg-slate-50/30">
                    <td className="py-2 px-3 text-left font-sans font-bold text-slate-800 dark:text-slate-200">
                      {row.year}
                    </td>
                    {MONTH_COLS.map((mCol) => {
                      const val = (row as Record<string, unknown>)[mCol.key] as number | null | undefined;
                      return (
                        <td
                          key={mCol.key}
                          className={`py-2 px-2 text-[11px] rounded transition-colors ${getCellColorClass(
                            val
                          )}`}
                        >
                          {val !== null && val !== undefined
                            ? `${(val * 100).toFixed(2)}%`
                            : "—"}
                        </td>
                      );
                    })}
                    <td
                      className={`py-2 px-3 font-bold text-xs ${
                        row.total >= 0 ? "text-emerald-700 dark:text-emerald-400 font-extrabold" : "text-rose-700 dark:text-rose-400 font-extrabold"
                      }`}
                    >
                      {(row.total * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reproducibility & Provenance Audit Panel (REQ-8.2) */}
      <AuditPanel runId={runId} />
    </div>
  );
}

