"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  fetchBacktestRuns,
  type BacktestStatusResponse,
} from "@/lib/api";
import {
  ArrowRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  Play,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";

function formatCurrency(val?: number | null): string {
  if (val == null) return "—";
  return `₹${val.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPercent(val?: number | null): string {
  if (val == null) return "—";
  const prefix = val > 0 ? "+" : "";
  return `${prefix}${(val * 100).toFixed(2)}%`;
}

function getStatusBadge(status: string) {
  switch (status.toLowerCase()) {
    case "completed":
      return (
        <Badge variant="success" className="capitalize flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
          Completed
        </Badge>
      );
    case "running":
      return (
        <Badge variant="secondary" className="capitalize flex items-center gap-1 bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
          <RefreshCw className="w-3 h-3 animate-spin text-blue-600 dark:text-blue-400" />
          Running
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive" className="capitalize flex items-center gap-1">
          <XCircle className="w-3 h-3" />
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="capitalize flex items-center gap-1">
          <Clock className="w-3 h-3 text-slate-500" />
          {status}
        </Badge>
      );
  }
}

export default function ReportsHubPage() {
  const [runs, setRuns] = useState<BacktestStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchBacktestRuns();
      setRuns(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load backtest reports history."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const completedRuns = runs.filter((r) => r.status.toLowerCase() === "completed");
  const latestCompleted = completedRuns[0] || null;

  return (
    <div className="space-y-8 pb-12 max-w-6xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Link href="/" className="hover:text-blue-600 transition-colors">
              Home
            </Link>
            <span>/</span>
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              Reports
            </span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Performance Reports & Analytics
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Institutional tear sheets, monthly return heatmaps, and export bundles for executed backtest runs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadRuns}
            disabled={loading}
            className="text-xs"
            data-testid="btn-refresh-reports"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button asChild size="sm" className="text-xs">
            <Link href="/backtest">
              <Play className="w-3.5 h-3.5 mr-1.5" />
              New Backtest
            </Link>
          </Button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          data-testid="reports-loading"
          className="flex flex-col items-center justify-center min-h-[300px] space-y-4"
        >
          <div className="h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-medium">
            Loading strategy reports...
          </p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div
          data-testid="reports-error"
          className="p-6 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-center space-y-3"
        >
          <h2 className="text-base font-semibold text-rose-800 dark:text-rose-300">
            Failed to Load Reports
          </h2>
          <p className="text-xs text-rose-700 dark:text-rose-200">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={loadRuns}
            className="text-xs border-rose-300 text-rose-800 hover:bg-rose-100 dark:border-rose-800 dark:text-rose-200"
          >
            Retry Loading
          </Button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && runs.length === 0 && (
        <Card
          data-testid="reports-empty"
          className="border-dashed border-2 border-slate-300 dark:border-slate-800 text-center py-12"
        >
          <CardContent className="space-y-4 max-w-md mx-auto">
            <div className="w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 mx-auto flex items-center justify-center">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold">No Backtest Reports Found</CardTitle>
              <CardDescription className="text-sm mt-1">
                Execute a historical backtest simulation or a parameter sweep to generate comprehensive performance reports and audit provenance logs.
              </CardDescription>
            </div>
            <div className="pt-2">
              <Button asChild>
                <Link href="/backtest">
                  <Play className="w-4 h-4 mr-2" />
                  Launch Backtest Engine
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Populated Content */}
      {!loading && !error && runs.length > 0 && (
        <div className="space-y-8">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Total Runs
              </span>
              <div
                data-testid="stat-total-runs"
                className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1"
              >
                {runs.length}
              </div>
              <span className="text-[11px] text-slate-500">Historical simulations</span>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Completed
              </span>
              <div
                data-testid="stat-completed-runs"
                className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1"
              >
                {completedRuns.length}
              </div>
              <span className="text-[11px] text-slate-500">With full analytics</span>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Latest Status
              </span>
              <div className="text-base font-semibold text-slate-900 dark:text-slate-100 mt-2">
                {getStatusBadge(runs[0].status)}
              </div>
              <span className="text-[11px] text-slate-500 truncate block mt-1">
                {new Date(runs[0].created_at).toLocaleDateString()}
              </span>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Top Return
              </span>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                {(() => {
                  const maxRet = Math.max(
                    ...completedRuns
                      .map((r) => r.total_return_pct ?? -Infinity)
                      .filter((v) => Number.isFinite(v)),
                    0
                  );
                  return maxRet !== 0 ? formatPercent(maxRet) : "—";
                })()}
              </div>
              <span className="text-[11px] text-slate-500">Across completed runs</span>
            </div>
          </div>

          {/* Latest Completed Run Highlight Card */}
          {latestCompleted && (
            <Card className="border-blue-100 dark:border-blue-900/50 bg-gradient-to-r from-blue-50/50 via-white to-slate-50/50 dark:from-blue-950/20 dark:via-slate-900 dark:to-slate-900 shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <Badge variant="outline" className="text-xs py-0.5 border-blue-200 text-blue-700 dark:text-blue-300">
                      Most Recent Simulation
                    </Badge>
                    <CardTitle className="text-lg font-bold mt-1">
                      Run <code className="text-sm font-mono text-blue-600 dark:text-blue-400">{latestCompleted.run_id}</code>
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Executed {new Date(latestCompleted.created_at).toLocaleString()} • Window: {latestCompleted.start_date || "N/A"} to {latestCompleted.end_date || "N/A"}
                    </CardDescription>
                  </div>
                  <Button asChild size="sm" className="sm:self-center">
                    <Link
                      href={`/reports/${latestCompleted.run_id}`}
                      data-testid="btn-view-latest-report"
                    >
                      View Full Performance Report
                      <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                    </Link>
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <div>
                    <span className="text-[11px] text-slate-500 block">Total Return</span>
                    <span
                      className={`text-sm font-bold flex items-center gap-1 mt-0.5 ${
                        (latestCompleted.total_return_pct ?? 0) >= 0
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-rose-600 dark:text-rose-400"
                      }`}
                    >
                      {(latestCompleted.total_return_pct ?? 0) >= 0 ? (
                        <TrendingUp className="w-3.5 h-3.5" />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5" />
                      )}
                      {formatPercent(latestCompleted.total_return_pct)}
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">CAGR</span>
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {formatPercent(latestCompleted.cagr)}
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">Max Drawdown</span>
                    <span className="text-sm font-bold text-rose-600 dark:text-rose-400 mt-0.5 block">
                      {latestCompleted.max_drawdown_pct != null
                        ? `-${(latestCompleted.max_drawdown_pct * 100).toFixed(2)}%`
                        : "—"}
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">Win Rate</span>
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {formatPercent(latestCompleted.win_rate)}
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-500 block">Trades Executed</span>
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {latestCompleted.total_trades ?? 0}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* All Runs Table */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm overflow-hidden space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  Historical Backtests & Reports
                </h2>
                <p className="text-xs text-slate-500">
                  Select any simulation to review KPIs, underwater drawdown curves, monthly heatmaps, and export bundles.
                </p>
              </div>
              <Badge variant="outline" className="text-xs">
                {runs.length} {runs.length === 1 ? "run" : "runs"}
              </Badge>
            </div>

            <div
              className="overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Historical backtest reports list"
            >
              <table
                data-testid="table-reports-list"
                className="w-full text-left border-collapse text-xs"
              >
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-slate-600 dark:text-slate-400">
                    <th className="py-3 px-3 font-semibold">Run ID</th>
                    <th className="py-3 px-3 font-semibold">Execution Date</th>
                    <th className="py-3 px-3 font-semibold">Simulation Period</th>
                    <th className="py-3 px-3 font-semibold">Status</th>
                    <th className="py-3 px-3 font-semibold text-right">Total Return</th>
                    <th className="py-3 px-3 font-semibold text-right">CAGR</th>
                    <th className="py-3 px-3 font-semibold text-right">Max Drawdown</th>
                    <th className="py-3 px-3 font-semibold text-right">Win Rate</th>
                    <th className="py-3 px-3 font-semibold text-right">Trades</th>
                    <th className="py-3 px-3 font-semibold text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                  {runs.map((run) => {
                    const isCompleted = run.status.toLowerCase() === "completed";
                    return (
                      <tr
                        key={run.run_id}
                        data-testid={`row-report-${run.run_id}`}
                        className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                      >
                        <td className="py-3 px-3 font-mono font-medium text-slate-800 dark:text-slate-200">
                          {isCompleted ? (
                            <Link
                              href={`/reports/${run.run_id}`}
                              className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                            >
                              <span>{run.run_id}</span>
                              <ExternalLink className="w-3 h-3 opacity-60" />
                            </Link>
                          ) : (
                            <span>{run.run_id}</span>
                          )}
                          {run.sweep_id && (
                            <Badge variant="outline" className="text-[10px] py-0 px-1 ml-1 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800">
                              Sweep
                            </Badge>
                          )}
                        </td>

                        <td className="py-3 px-3 text-slate-600 dark:text-slate-400">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-500" />
                            {new Date(run.created_at).toLocaleDateString()}
                          </span>
                        </td>

                        <td className="py-3 px-3 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                          {run.start_date && run.end_date ? (
                            `${run.start_date} → ${run.end_date}`
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>

                        <td className="py-3 px-3">
                          {getStatusBadge(run.status)}
                        </td>

                        <td
                          className={`py-3 px-3 text-right font-semibold font-mono ${
                            (run.total_return_pct ?? 0) >= 0
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-rose-600 dark:text-rose-400"
                          }`}
                        >
                          {formatPercent(run.total_return_pct)}
                        </td>

                        <td className="py-3 px-3 text-right font-mono text-slate-700 dark:text-slate-300">
                          {formatPercent(run.cagr)}
                        </td>

                        <td className="py-3 px-3 text-right font-mono text-rose-600 dark:text-rose-400">
                          {run.max_drawdown_pct != null
                            ? `-${(run.max_drawdown_pct * 100).toFixed(2)}%`
                            : "—"}
                        </td>

                        <td className="py-3 px-3 text-right font-mono text-slate-700 dark:text-slate-300">
                          {formatPercent(run.win_rate)}
                        </td>

                        <td className="py-3 px-3 text-right font-mono text-slate-700 dark:text-slate-300">
                          {run.total_trades ?? "—"}
                        </td>

                        <td className="py-3 px-3 text-center">
                          {isCompleted ? (
                            <Button asChild variant="outline" size="sm" className="h-7 px-2.5 text-xs">
                              <Link
                                href={`/reports/${run.run_id}`}
                                data-testid={`btn-view-${run.run_id}`}
                              >
                                View Report
                              </Link>
                            </Button>
                          ) : (
                            <span className="text-slate-500 text-[11px]">Pending</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
