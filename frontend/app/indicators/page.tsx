"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Calendar,
  Check,
  Eye,
  EyeOff,
  Filter,
  LineChart as LineChartIcon,
  RefreshCw,
  Sliders,
} from "lucide-react";
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

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fetchIndicators, IndicatorItem } from "@/lib/api";

const PRESET_SYMBOLS = [
  "BALKRISIND",
  "FEDERALBNK",
  "TATAELXSI",
  "AUBANK",
  "ASHOKLEY",
];

export default function IndicatorsPage() {
  const [selectedSymbol, setSelectedSymbol] = React.useState<string>("BALKRISIND");
  const [startDate, setStartDate] = React.useState<string>("2021-01-01");
  const [endDate, setEndDate] = React.useState<string>("2023-12-31");

  // Indicator visibility toggles
  const [showPrice, setShowPrice] = React.useState<boolean>(true);
  const [showEma20, setShowEma20] = React.useState<boolean>(true);
  const [showEma50, setShowEma50] = React.useState<boolean>(true);
  const [showEma150, setShowEma150] = React.useState<boolean>(true);
  const [showEma200, setShowEma200] = React.useState<boolean>(true);
  const [showHigh52w, setShowHigh52w] = React.useState<boolean>(false);

  // Query indicators
  const indicatorsQuery = useQuery({
    queryKey: ["indicators", selectedSymbol, startDate, endDate],
    queryFn: () => fetchIndicators(selectedSymbol, startDate, endDate),
    enabled: !!selectedSymbol,
  });

  const chartData: IndicatorItem[] = indicatorsQuery.data?.indicators || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
          Technical Indicators & EMA Preview
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Inspect 20, 50, 150, 200 EMAs on Adjusted Close and rolling 252-day 52-week highs.
        </p>
      </div>

      {/* Control Card */}
      <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sliders className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-lg">Configuration & Filters</CardTitle>
            </div>
            <Badge variant="outline" className="text-xs">
              Vectorized TA Engine
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Adjust active symbol, historical time window, and indicator series visibility.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* Symbol Picker */}
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Symbol:
              </label>
              <select
                data-testid="indicator-symbol-select"
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono font-semibold"
              >
                {PRESET_SYMBOLS.map((sym) => (
                  <option key={sym} value={sym}>
                    {sym}
                  </option>
                ))}
              </select>
            </div>

            {/* Start Date */}
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Start:
              </label>
              <input
                type="date"
                data-testid="indicator-start-date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
              />
            </div>

            {/* End Date */}
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                End:
              </label>
              <input
                type="date"
                data-testid="indicator-end-date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => indicatorsQuery.refetch()}
              disabled={indicatorsQuery.isFetching}
              className="ml-auto text-xs"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 mr-1.5 ${
                  indicatorsQuery.isFetching ? "animate-spin text-blue-600" : ""
                }`}
              />
              Refresh
            </Button>
          </div>

          {/* Interactive Legend & Series Toggles */}
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 mr-2 flex items-center">
              <Filter className="w-3.5 h-3.5 mr-1" /> Toggle Series:
            </span>

            {/* Price Toggle */}
            <button
              type="button"
              data-testid="toggle-price"
              onClick={() => setShowPrice((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors flex items-center space-x-1.5 ${
                showPrice
                  ? "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800"
                  : "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-500 dark:border-slate-700 line-through"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-blue-600" />
              <span>Adj Close</span>
            </button>

            {/* EMA 20 Toggle */}
            <button
              type="button"
              data-testid="toggle-ema-20"
              onClick={() => setShowEma20((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors flex items-center space-x-1.5 ${
                showEma20
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800"
                  : "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-500 dark:border-slate-700 line-through"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>EMA 20</span>
            </button>

            {/* EMA 50 Toggle */}
            <button
              type="button"
              data-testid="toggle-ema-50"
              onClick={() => setShowEma50((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors flex items-center space-x-1.5 ${
                showEma50
                  ? "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800"
                  : "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-500 dark:border-slate-700 line-through"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>EMA 50</span>
            </button>

            {/* EMA 150 Toggle */}
            <button
              type="button"
              data-testid="toggle-ema-150"
              onClick={() => setShowEma150((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors flex items-center space-x-1.5 ${
                showEma150
                  ? "bg-purple-50 text-purple-700 border-purple-300 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800"
                  : "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-500 dark:border-slate-700 line-through"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>EMA 150</span>
            </button>

            {/* EMA 200 Toggle */}
            <button
              type="button"
              data-testid="toggle-ema-200"
              onClick={() => setShowEma200((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors flex items-center space-x-1.5 ${
                showEma200
                  ? "bg-red-50 text-red-700 border-red-300 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800"
                  : "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-500 dark:border-slate-700 line-through"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span>EMA 200</span>
            </button>

            {/* 52W High Toggle */}
            <button
              type="button"
              data-testid="toggle-high-52w"
              onClick={() => setShowHigh52w((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors flex items-center space-x-1.5 ${
                showHigh52w
                  ? "bg-indigo-50 text-indigo-700 border-indigo-300 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800"
                  : "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-500 dark:border-slate-700 line-through"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              <span>52W High</span>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Chart Section */}
      <Card
        className="border-slate-200 dark:border-slate-800 shadow-sm"
        data-testid="indicator-chart-card"
      >
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <LineChartIcon className="w-5 h-5 text-indigo-600" />
              <CardTitle className="text-lg">
                Technical Chart: <span className="text-blue-600">{selectedSymbol}</span>
              </CardTitle>
            </div>
            {indicatorsQuery.data && (
              <Badge variant="secondary" className="text-xs">
                {indicatorsQuery.data.count} Sessions
              </Badge>
            )}
          </div>
          <CardDescription className="text-xs">
            Visual inspection of trend alignment: EMA 20 &gt; EMA 50 &gt; EMA 150 &gt; EMA 200.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {indicatorsQuery.isLoading ? (
            <div className="py-24 flex flex-col items-center justify-center space-y-2 text-slate-500">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <p className="text-xs">Loading indicators for {selectedSymbol}...</p>
            </div>
          ) : indicatorsQuery.isError ? (
            <div className="py-16 text-center text-xs text-red-500">
              Failed to load indicators for {selectedSymbol}. Ensure prices are available.
            </div>
          ) : chartData.length > 0 ? (
            <div data-testid="indicator-chart" className="w-full h-96 pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(val: string) => val.slice(0, 7)}
                    minTickGap={40}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(val: number) => `₹${val}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15, 23, 42, 0.9)",
                      borderRadius: "0.5rem",
                      borderColor: "#334155",
                      fontSize: "12px",
                      color: "#f8fafc",
                    }}
                    formatter={(val: number) => [`₹${val?.toFixed(2) ?? "—"}`, ""]}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />

                  {/* Price Line */}
                  {showPrice && (
                    <Line
                      type="monotone"
                      dataKey="adj_close"
                      name="Adjusted Close"
                      stroke="#3b82f6"
                      strokeWidth={1.5}
                      dot={false}
                    />
                  )}

                  {/* 4 EMA Lines */}
                  {showEma20 && (
                    <Line
                      type="monotone"
                      dataKey="ema_20"
                      name="EMA 20"
                      stroke="#10b981"
                      strokeWidth={1.5}
                      dot={false}
                      className="ema-line"
                    />
                  )}

                  {showEma50 && (
                    <Line
                      type="monotone"
                      dataKey="ema_50"
                      name="EMA 50"
                      stroke="#f59e0b"
                      strokeWidth={1.5}
                      dot={false}
                      className="ema-line"
                    />
                  )}

                  {showEma150 && (
                    <Line
                      type="monotone"
                      dataKey="ema_150"
                      name="EMA 150"
                      stroke="#8b5cf6"
                      strokeWidth={1.5}
                      dot={false}
                      className="ema-line"
                    />
                  )}

                  {showEma200 && (
                    <Line
                      type="monotone"
                      dataKey="ema_200"
                      name="EMA 200"
                      stroke="#ef4444"
                      strokeWidth={1.5}
                      dot={false}
                      className="ema-line"
                    />
                  )}

                  {/* 52W High Line */}
                  {showHigh52w && (
                    <Line
                      type="monotone"
                      dataKey="high_52w"
                      name="52W High"
                      stroke="#6366f1"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-slate-400">
              No indicator data available for the selected range.
            </div>
          )}
        </CardContent>

        <CardFooter className="border-t border-slate-100 dark:border-slate-800 pt-3 text-xs text-slate-500 flex justify-between">
          <span>All EMAs computed via pandas .ewm(span, adjust=False) with min_periods warm-up.</span>
          <span>52W High lookback: 252 sessions (shifted by 1 to exclude bar N).</span>
        </CardFooter>
      </Card>
    </div>
  );
}
