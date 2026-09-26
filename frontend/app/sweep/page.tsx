"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  type BacktestCompareResponse,
  compareBacktestRuns,
  type EquityPoint,
  fetchSweepStatus,
  runSweep,
  type SweepRunItem,
  type SweepStatusResponse,
} from "../../lib/api";

interface GridParamEntry {
  param: string;
  values: string[];
}

const AVAILABLE_PARAMS = [
  { key: "sl_pct", label: "Stop Loss % (e.g. 5, 6, 7)" },
  { key: "risk_pct", label: "Risk % (e.g. 1, 2, 3)" },
  { key: "cost_bps", label: "Cost bps (e.g. 5, 10, 20)" },
  { key: "high_52w_factor", label: "52W High Factor (e.g. 0.85, 0.90)" },
  { key: "capital", label: "Capital (e.g. 250000, 500000)" },
  { key: "ranking_rule", label: "Ranking Rule (momentum, alphabetical, 52w_proximity)" },
];

const LINE_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#6366f1"];

export default function SweepPage() {
  // Form State
  const [startDate, setStartDate] = useState<string>("2020-06-01");
  const [endDate, setEndDate] = useState<string>("2022-04-29");
  const [initialCapital, setInitialCapital] = useState<string>("500000");

  const [gridEntries, setGridEntries] = useState<GridParamEntry[]>([
    { param: "sl_pct", values: ["5", "7"] },
    { param: "risk_pct", values: ["1", "2"] },
  ]);

  const [selectedParamToAdd, setSelectedParamToAdd] = useState<string>("cost_bps");
  const [newValInputs, setNewValInputs] = useState<Record<string, string>>({});

  // Sweep Execution State
  const [activeSweepId, setActiveSweepId] = useState<string | null>(null);
  const [sweepStatus, setSweepStatus] = useState<string>("idle");
  const [sweepData, setSweepData] = useState<SweepStatusResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Compare State
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [compareData, setCompareData] = useState<BacktestCompareResponse | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  // Total permutations count
  const totalPermutations = useMemo(() => {
    if (gridEntries.length === 0) return 0;
    return gridEntries.reduce((acc, curr) => acc * Math.max(curr.values.length, 1), 1);
  }, [gridEntries]);

  // Handle adding a new parameter row
  const handleAddParam = () => {
    if (gridEntries.some((e) => e.param === selectedParamToAdd)) return;
    setGridEntries([...gridEntries, { param: selectedParamToAdd, values: [] }]);
  };

  // Handle removing a parameter row
  const handleRemoveParam = (paramKey: string) => {
    setGridEntries(gridEntries.filter((e) => e.param !== paramKey));
  };

  // Handle adding a value to a parameter
  const handleAddValue = (paramKey: string) => {
    const val = newValInputs[paramKey]?.trim();
    if (!val) return;
    setGridEntries(
      gridEntries.map((e) => {
        if (e.param === paramKey) {
          if (!e.values.includes(val)) {
            return { ...e, values: [...e.values, val] };
          }
        }
        return e;
      })
    );
    setNewValInputs({ ...newValInputs, [paramKey]: "" });
  };

  // Handle removing a value from a parameter
  const handleRemoveValue = (paramKey: string, valToRemove: string) => {
    setGridEntries(
      gridEntries.map((e) => {
        if (e.param === paramKey) {
          return { ...e, values: e.values.filter((v) => v !== valToRemove) };
        }
        return e;
      })
    );
  };

  // Trigger Sweep
  const handleRunSweep = async () => {
    try {
      setErrorMessage(null);
      setSelectedRunIds([]);
      setIsCompareOpen(false);

      const paramGridObj: Record<string, (string | number)[]> = {};
      for (const entry of gridEntries) {
        if (entry.values.length === 0) {
          setErrorMessage(`Parameter '${entry.param}' must have at least one value.`);
          return;
        }
        paramGridObj[entry.param] = entry.values.map((v) => {
          const num = Number(v);
          return isNaN(num) ? v : num;
        });
      }

      setSweepStatus("pending");
      const resp = await runSweep({
        start: startDate || null,
        end: endDate || null,
        base_config: {
          capital: Number(initialCapital) || 500000.0,
        },
        param_grid: paramGridObj,
      });

      setActiveSweepId(resp.sweep_id);
    } catch (err: unknown) {
      setSweepStatus("failed");
      setErrorMessage(err instanceof Error ? err.message : "Failed to trigger parameter sweep");
    }
  };

  // Polling Effect
  useEffect(() => {
    if (!activeSweepId || (sweepStatus !== "pending" && sweepStatus !== "running")) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const data = await fetchSweepStatus(activeSweepId);
        setSweepData(data);
        setSweepStatus(data.status);

        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch (err: unknown) {
        setErrorMessage(err instanceof Error ? err.message : "Error polling sweep status");
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeSweepId, sweepStatus]);

  // Toggle selection for comparison
  const handleToggleSelectRun = (runId: string) => {
    if (selectedRunIds.includes(runId)) {
      setSelectedRunIds(selectedRunIds.filter((id) => id !== runId));
    } else {
      setSelectedRunIds([...selectedRunIds, runId]);
    }
  };

  const handleSelectAllRuns = () => {
    if (!sweepData) return;
    if (selectedRunIds.length === sweepData.runs.length) {
      setSelectedRunIds([]);
    } else {
      setSelectedRunIds(sweepData.runs.map((r) => r.run_id));
    }
  };

  // Open Compare Drawer
  const handleOpenCompare = useCallback(async () => {
    if (selectedRunIds.length === 0) return;
    try {
      setIsComparing(true);
      setIsCompareOpen(true);
      const res = await compareBacktestRuns(selectedRunIds);
      setCompareData(res);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load comparison data");
    } finally {
      setIsComparing(false);
    }
  }, [selectedRunIds]);

  // Aligned chart data for comparison overlaid equity curves
  const compareChartData = useMemo(() => {
    if (!compareData || !compareData.equity_curves) return [];
    const dateMap = new Map<string, Record<string, number | string>>();

    for (const [runId, curve] of Object.entries(compareData.equity_curves)) {
      for (const pt of curve as EquityPoint[]) {
        if (!dateMap.has(pt.date)) {
          dateMap.set(pt.date, { date: pt.date });
        }
        dateMap.get(pt.date)![runId] = pt.equity;
      }
    }

    const sortedDates = Array.from(dateMap.keys()).sort();
    return sortedDates.map((d) => dateMap.get(d)!);
  }, [compareData]);

  // 2D Heatmap Matrix generation
  const heatmapData = useMemo(() => {
    if (!sweepData || gridEntries.length !== 2) return null;
    const p1 = gridEntries[0].param;
    const p2 = gridEntries[1].param;

    const rowVals = Array.from(new Set(sweepData.runs.map((r) => String(r.params[p1]))));
    const colVals = Array.from(new Set(sweepData.runs.map((r) => String(r.params[p2]))));

    const matrix: Record<string, Record<string, SweepRunItem | null>> = {};
    for (const r of rowVals) {
      matrix[r] = {};
      for (const c of colVals) {
        matrix[r][c] = null;
      }
    }

    for (const item of sweepData.runs) {
      const r = String(item.params[p1]);
      const c = String(item.params[p2]);
      if (matrix[r]) {
        matrix[r][c] = item;
      }
    }

    return { p1, p2, rowVals, colVals, matrix };
  }, [sweepData, gridEntries]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Parameter & Scenario Sweep
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Explore sensitivity across strategy parameters, evaluate regimes, and compare scenario outcomes side-by-side.
        </p>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 text-sm">
          {errorMessage}
        </div>
      )}

      {/* Grid Builder & Base Config Card */}
      <div className="p-4 sm:p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Dynamic Parameter Grid Builder
        </h2>

        {/* Base Dates & Capital */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <label
              htmlFor="sweep-start-date"
              className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1"
            >
              Start Date
            </label>
            <input
              id="sweep-start-date"
              type="date"
              aria-label="Start Date"
              data-testid="input-start-date"
              className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label
              htmlFor="sweep-end-date"
              className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1"
            >
              End Date
            </label>
            <input
              id="sweep-end-date"
              type="date"
              aria-label="End Date"
              data-testid="input-end-date"
              className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div>
            <label
              htmlFor="sweep-capital"
              className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1"
            >
              Starting Capital (₹)
            </label>
            <input
              id="sweep-capital"
              type="number"
              aria-label="Starting Capital"
              data-testid="input-capital"
              className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
            />
          </div>
        </div>

        {/* Dynamic Grid Rows */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Swept Factors & Candidate Values
            </span>
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <select
                aria-label="Select factor to add"
                className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 w-full sm:w-auto max-w-full"
                value={selectedParamToAdd}
                onChange={(e) => setSelectedParamToAdd(e.target.value)}
              >
                {AVAILABLE_PARAMS.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleAddParam}
                className="w-full sm:w-auto text-center px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
              >
                + Add Factor
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {gridEntries.map((entry) => (
              <div
                key={entry.param}
                className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 px-2 py-1 rounded">
                    {entry.param}
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {entry.values.map((v) => (
                      <span
                        key={v}
                        className="inline-flex items-center text-xs px-2 py-0.5 rounded-md bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-mono text-slate-900 dark:text-slate-100"
                      >
                        {v}
                        <button
                          type="button"
                          aria-label={`Remove value ${v} for ${entry.param}`}
                          onClick={() => handleRemoveValue(entry.param, v)}
                          className="ml-1 text-slate-500 hover:text-rose-500 font-bold"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                    {entry.values.length === 0 && (
                      <span className="text-xs text-slate-600 dark:text-slate-400 italic">No values added</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="text"
                    placeholder="Add value..."
                    aria-label={`Add value for ${entry.param}`}
                    className="text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 w-24"
                    value={newValInputs[entry.param] || ""}
                    onChange={(e) =>
                      setNewValInputs({ ...newValInputs, [entry.param]: e.target.value })
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddValue(entry.param);
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => handleAddValue(entry.param)}
                    className="px-2.5 py-1 text-xs rounded bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300"
                  >
                    Add
                  </button>
                  <button
                    type="button"
                    aria-label={`Remove factor ${entry.param}`}
                    onClick={() => handleRemoveParam(entry.param)}
                    className="text-xs text-rose-600 hover:text-rose-700 px-2 py-1"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer info & Run Button */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2 text-sm text-slate-600 dark:text-slate-400">
            <span>Total Permutations:</span>
            <span className="font-bold text-slate-900 dark:text-slate-100 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
              {totalPermutations} runs
            </span>
          </div>

          <button
            type="button"
            data-testid="btn-run-sweep"
            onClick={handleRunSweep}
            disabled={sweepStatus === "running" || totalPermutations === 0}
            className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors shadow-sm disabled:opacity-50"
          >
            {sweepStatus === "running" ? "Running Sweep..." : "Run Parameter Sweep"}
          </button>
        </div>
      </div>

      {/* Sweep Progress & Results View */}
      {sweepData && (
        <div className="space-y-6">
          {/* Progress Banner */}
          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div
                className={`h-3 w-3 rounded-full ${
                  sweepData.status === "completed"
                    ? "bg-emerald-500"
                    : sweepData.status === "running"
                    ? "bg-blue-500 animate-pulse"
                    : "bg-slate-400"
                }`}
              />
              <span className="font-semibold text-sm capitalize">
                Sweep Status: {sweepData.status}
              </span>
              <span className="text-xs text-slate-600 dark:text-slate-400">
                ({sweepData.completed_runs} / {sweepData.total_runs} completed)
              </span>
            </div>

            {/* Selection compare button */}
            <button
              type="button"
              data-testid="btn-open-compare"
              onClick={handleOpenCompare}
              disabled={selectedRunIds.length < 1}
              className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-40"
            >
              Compare Selected ({selectedRunIds.length})
            </button>
          </div>

          {/* 2D Heatmap if 2 parameters swept */}
          {heatmapData && (
            <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Sensitivity Heatmap (CAGR % by {heatmapData.p1} vs {heatmapData.p2})
              </h3>
              <div
                className="overflow-x-auto"
                tabIndex={0}
                role="region"
                aria-label="Sensitivity heatmap"
              >
                <table className="min-w-full text-center text-xs border border-slate-200 dark:border-slate-800">
                  <thead>
                    <tr className="bg-slate-100 dark:bg-slate-800">
                      <th className="p-2 border border-slate-200 dark:border-slate-700 font-mono">
                        {heatmapData.p1} \ {heatmapData.p2}
                      </th>
                      {heatmapData.colVals.map((col) => (
                        <th
                          key={col}
                          className="p-2 border border-slate-200 dark:border-slate-700 font-mono font-semibold"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heatmapData.rowVals.map((row) => (
                      <tr key={row}>
                        <td className="p-2 border border-slate-200 dark:border-slate-700 font-mono font-semibold bg-slate-50 dark:bg-slate-800/60">
                          {row}
                        </td>
                        {heatmapData.colVals.map((col) => {
                          const item = heatmapData.matrix[row]?.[col];
                          const cagr = item?.cagr;
                          const hasVal = cagr !== null && cagr !== undefined;
                          const cagrPct = hasVal ? (cagr * 100).toFixed(2) : null;
                          const isPos = hasVal && cagr > 0;
                          const isNeg = hasVal && cagr < 0;

                          return (
                            <td
                              key={col}
                              className={`p-2.5 border border-slate-200 dark:border-slate-700 font-mono font-semibold ${
                                isPos
                                  ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300"
                                  : isNeg
                                  ? "bg-rose-500/20 text-rose-700 dark:text-rose-300"
                                  : "bg-slate-50 dark:bg-slate-800/40 text-slate-600 dark:text-slate-400"
                              }`}
                            >
                              {hasVal ? `${isPos ? "+" : ""}${cagrPct}%` : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Runs Table */}
          <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Sweep Runs Breakdown
              </h3>
              <button
                type="button"
                onClick={handleSelectAllRuns}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                {selectedRunIds.length === sweepData.runs.length
                  ? "Deselect All"
                  : "Select All"}
              </button>
            </div>

            <div
              className="overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Sweep runs breakdown table"
            >
              <table
                data-testid="sweep-runs-table"
                className="min-w-full text-left text-xs divide-y divide-slate-200 dark:divide-slate-800"
              >
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400">
                    <th className="p-2.5 w-8"></th>
                    <th className="p-2.5">Run ID</th>
                    <th className="p-2.5">Parameters</th>
                    <th className="p-2.5">Final Capital</th>
                    <th className="p-2.5">Return %</th>
                    <th className="p-2.5">CAGR %</th>
                    <th className="p-2.5">Win Rate</th>
                    <th className="p-2.5">Trades</th>
                    <th className="p-2.5">Max DD %</th>
                    <th className="p-2.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                  {sweepData.runs.map((r) => {
                    const isSelected = selectedRunIds.includes(r.run_id);
                    return (
                      <tr
                        key={r.run_id}
                        className={`hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors ${
                          isSelected ? "bg-blue-50/50 dark:bg-blue-950/20" : ""
                        }`}
                      >
                        <td className="p-2.5">
                          <input
                            type="checkbox"
                            aria-label={`Select run ${r.run_id} for comparison`}
                            data-testid={`checkbox-run-${r.run_id}`}
                            checked={isSelected}
                            onChange={() => handleToggleSelectRun(r.run_id)}
                            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                        </td>
                        <td className="p-2.5 font-bold text-slate-900 dark:text-slate-100">
                          {r.run_id}
                        </td>
                        <td className="p-2.5">
                          {Object.entries(r.params).map(([k, v]) => (
                            <span
                              key={k}
                              className="mr-1.5 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                            >
                              {k}: {String(v)}
                            </span>
                          ))}
                        </td>
                        <td className="p-2.5">
                          {r.final_capital != null
                            ? `₹${r.final_capital.toLocaleString()}`
                            : "—"}
                        </td>
                        <td
                          className={`p-2.5 font-semibold ${
                            r.total_return_pct && r.total_return_pct > 0
                              ? "text-emerald-600 dark:text-emerald-400"
                              : r.total_return_pct && r.total_return_pct < 0
                              ? "text-rose-600 dark:text-rose-400"
                              : ""
                          }`}
                        >
                          {r.total_return_pct != null
                            ? `${(r.total_return_pct * 100).toFixed(2)}%`
                            : "—"}
                        </td>
                        <td className="p-2.5">
                          {r.cagr != null ? `${(r.cagr * 100).toFixed(2)}%` : "—"}
                        </td>
                        <td className="p-2.5">
                          {r.win_rate != null ? `${(r.win_rate * 100).toFixed(1)}%` : "—"}
                        </td>
                        <td className="p-2.5">{r.total_trades ?? "—"}</td>
                        <td className="p-2.5">
                          {r.max_drawdown_pct != null
                            ? `${(r.max_drawdown_pct * 100).toFixed(2)}%`
                            : "—"}
                        </td>
                        <td className="p-2.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                              r.status === "completed"
                                ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-300"
                                : r.status === "running"
                                ? "bg-blue-100 text-blue-900 dark:bg-blue-950 dark:text-blue-300"
                                : "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-200"
                            }`}
                          >
                            {r.status}
                          </span>
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

      {/* Compare Drawer / Modal */}
      {isCompareOpen && (
        <div
          data-testid="compare-drawer"
          className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-sm flex justify-end"
        >
          <div className="w-full max-w-4xl bg-white dark:bg-slate-900 h-full p-6 shadow-2xl flex flex-col space-y-6 overflow-y-auto">
            {/* Drawer Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  Multi-Run Comparison ({selectedRunIds.length} runs)
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  Overlaid daily equity curves and aligned parameter diffs.
                </p>
              </div>
              <button
                type="button"
                data-testid="btn-close-compare"
                onClick={() => setIsCompareOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sm font-semibold"
              >
                Close
              </button>
            </div>

            {isComparing ? (
              <div className="p-12 text-center text-sm text-slate-600 dark:text-slate-400">
                Loading comparison curves and metrics...
              </div>
            ) : compareData ? (
              <div className="space-y-6">
                {/* Overlaid Equity Chart */}
                <div
                  data-testid="compare-chart"
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40"
                >
                  <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-4">
                    Overlaid Mark-to-Market Equity Curves
                  </h4>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={compareChartData}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10 }}
                          tickFormatter={(d: string) => d.slice(5)}
                        />
                        <YAxis
                          tick={{ fontSize: 10 }}
                          domain={["auto", "auto"]}
                          tickFormatter={(v: number) => `₹${(v / 1000).toFixed(0)}k`}
                        />
                        <Tooltip />
                        <Legend />
                        {selectedRunIds.map((rid, idx) => (
                          <Line
                            key={rid}
                            type="monotone"
                            dataKey={rid}
                            name={rid}
                            stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                            dot={false}
                            strokeWidth={2}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Aligned Metrics Diff Table */}
                <div
                  className="overflow-x-auto"
                  tabIndex={0}
                  role="region"
                  aria-label="Run comparison metrics table"
                >
                  <table className="min-w-full text-left text-xs divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800">
                    <thead className="bg-slate-100 dark:bg-slate-800">
                      <tr>
                        <th className="p-2.5 font-bold text-slate-900 dark:text-slate-100">Metric / Parameter</th>
                        {selectedRunIds.map((rid) => (
                          <th key={rid} className="p-2.5 font-bold font-mono text-slate-900 dark:text-slate-100">
                            {rid}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                      <tr>
                        <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">Final Capital</td>
                        {selectedRunIds.map((rid) => (
                          <td key={rid} className="p-2">
                            ₹{compareData.runs[rid]?.final_capital?.toLocaleString() ?? "—"}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">Total Return %</td>
                        {selectedRunIds.map((rid) => {
                          const val = compareData.runs[rid]?.total_return_pct;
                          return (
                            <td
                              key={rid}
                              className={`p-2 font-bold ${
                                val && val > 0
                                  ? "text-emerald-700 dark:text-emerald-400"
                                  : val && val < 0
                                  ? "text-rose-700 dark:text-rose-400"
                                  : ""
                              }`}
                            >
                              {val != null ? `${(val * 100).toFixed(2)}%` : "—"}
                            </td>
                          );
                        })}
                      </tr>
                      <tr>
                        <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">CAGR %</td>
                        {selectedRunIds.map((rid) => (
                          <td key={rid} className="p-2">
                            {compareData.runs[rid]?.cagr != null
                              ? `${(compareData.runs[rid]!.cagr! * 100).toFixed(2)}%`
                              : "—"}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">Win Rate</td>
                        {selectedRunIds.map((rid) => (
                          <td key={rid} className="p-2">
                            {compareData.runs[rid]?.win_rate != null
                              ? `${(compareData.runs[rid]!.win_rate! * 100).toFixed(1)}%`
                              : "—"}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">Total Trades</td>
                        {selectedRunIds.map((rid) => (
                          <td key={rid} className="p-2">
                            {compareData.runs[rid]?.total_trades ?? "—"}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">Max Drawdown %</td>
                        {selectedRunIds.map((rid) => (
                          <td key={rid} className="p-2">
                            {compareData.runs[rid]?.max_drawdown_pct != null
                              ? `${(
                                  compareData.runs[rid]!.max_drawdown_pct! * 100
                                ).toFixed(2)}%`
                              : "—"}
                          </td>
                        ))}
                      </tr>
                      {/* Parameters Diffs */}
                      {["sl_pct", "risk_pct", "cost_bps", "ranking_rule"].map((paramKey) => (
                        <tr key={paramKey} className="bg-slate-50/50 dark:bg-slate-800/30">
                          <td className="p-2 font-semibold text-slate-600 dark:text-slate-400">
                            param: {paramKey}
                          </td>
                          {selectedRunIds.map((rid) => (
                            <td key={rid} className="p-2 text-blue-600 dark:text-blue-400">
                              {String(compareData.runs[rid]?.config?.[paramKey] ?? "—")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
