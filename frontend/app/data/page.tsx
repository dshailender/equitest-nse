"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpDown,
  BarChart2,
  Calendar,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  Info,
  Layers,
  LineChart as LineChartIcon,
  RefreshCw,
  Search,
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
import {
  ConstituentDetail,
  CoverageItem,
  fetchCoverage,
  fetchPrices,
  fetchUniverse,
  triggerIngest,
} from "@/lib/api";

export default function DataStatusPage() {
  const queryClient = useQueryClient();

  // Ingest state
  const [startDate, setStartDate] = React.useState("2020-01-01");
  const [endDate, setEndDate] = React.useState("2023-12-31");
  const [ingestScope, setIngestScope] = React.useState<"smoke" | "midcap" | "full" | "custom">("smoke");
  const [customSymbols, setCustomSymbols] = React.useState("");
  const [ingestFeedback, setIngestFeedback] = React.useState<{
    type: "success" | "warning" | "error";
    message: string;
    details?: string[];
  } | null>(null);

  // Universe state
  const [universeDate, setUniverseDate] = React.useState("2022-01-01");

  // Selected symbol for prices drilldown
  const [selectedSymbol, setSelectedSymbol] = React.useState<string>("RELIANCE");

  // Pagination & filter state for coverage
  const [page, setPage] = React.useState(1);
  const pageSize = 5;
  const [searchFilter, setSearchFilter] = React.useState("");

  // Queries
  const coverageQuery = useQuery({
    queryKey: ["coverage"],
    queryFn: fetchCoverage,
  });

  const universeQuery = useQuery({
    queryKey: ["universe", universeDate],
    queryFn: () => fetchUniverse(universeDate),
  });

  const pricesQuery = useQuery({
    queryKey: ["prices", selectedSymbol],
    queryFn: () => fetchPrices(selectedSymbol),
    enabled: !!selectedSymbol,
  });

  // Ingestion Mutation
  const ingestMutation = useMutation({
    mutationFn: (variables?: { start?: string; end?: string; symbols?: string[]; scope?: string }) => {
      const s = variables?.start ?? startDate;
      const e = variables?.end ?? endDate;
      const sc = variables?.scope ?? ingestScope;
      let syms = variables?.symbols;
      if (syms === undefined && sc === "custom") {
        syms = customSymbols
          .split(",")
          .map((sym) => sym.trim().toUpperCase())
          .filter(Boolean);
      }
      return triggerIngest(s, e, syms, sc);
    },
    onSuccess: (data) => {
      if (data.status === "failed") {
        setIngestFeedback({
          type: "error",
          message: `Ingestion failed (Job ID: ${data.job_id.slice(0, 8)}): 0 rows ingested across ${data.symbols_ingested} symbols.`,
          details: data.errors && data.errors.length > 0 ? data.errors : undefined,
        });
      } else if (data.status === "partial" || (data.errors && data.errors.length > 0)) {
        setIngestFeedback({
          type: "warning",
          message: `Partially ingested ${data.rows_ingested} rows across ${data.symbols_ingested} symbols (Job ID: ${data.job_id.slice(0, 8)}).`,
          details: data.errors && data.errors.length > 0 ? data.errors : undefined,
        });
      } else {
        setIngestFeedback({
          type: "success",
          message: `Ingested ${data.rows_ingested} rows across ${data.symbols_ingested} symbols (Job ID: ${data.job_id.slice(0, 8)}).`,
        });
      }
      queryClient.invalidateQueries({ queryKey: ["coverage"] });
      queryClient.invalidateQueries({ queryKey: ["universe"] });
      queryClient.invalidateQueries({ queryKey: ["prices", selectedSymbol] });
    },
    onError: (err) => {
      setIngestFeedback({
        type: "error",
        message: `Ingest failed: ${err instanceof Error ? err.message : String(err)}`,
      });
    },
  });

  const handleStartIngest = () => {
    let targetSymbols: string[] | undefined = undefined;
    if (ingestScope === "custom") {
      targetSymbols = customSymbols
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);
    }
    ingestMutation.mutate({
      start: startDate,
      end: endDate,
      symbols: targetSymbols,
      scope: ingestScope,
    });
  };

  // Filter & paginate coverage items
  const allCoverage = React.useMemo(
    () => coverageQuery.data?.items || [],
    [coverageQuery.data]
  );
  const filteredCoverage = allCoverage.filter((item) =>
    item.symbol.toLowerCase().includes(searchFilter.toLowerCase())
  );
  const totalPages = Math.max(1, Math.ceil(filteredCoverage.length / pageSize));
  const paginatedCoverage = filteredCoverage.slice((page - 1) * pageSize, page * pageSize);

  // Universe pagination & filter state
  const [universePage, setUniversePage] = React.useState(1);
  const universePageSize = 5;
  const [universeSearch, setUniverseSearch] = React.useState("");

  // Filter & paginate universe constituents
  const allUniverseDetails: ConstituentDetail[] = React.useMemo(() => {
    if (universeQuery.data?.details && universeQuery.data.details.length > 0) {
      return universeQuery.data.details;
    }
    return (universeQuery.data?.tickers || []).map((sym, idx) => ({
      symbol: sym,
      name: sym,
      rank: 101 + idx,
      sector: "Diversified",
    }));
  }, [universeQuery.data]);

  const filteredUniverse = React.useMemo(() => {
    const q = universeSearch.toLowerCase().trim();
    if (!q) return allUniverseDetails;
    return allUniverseDetails.filter(
      (item) =>
        item.symbol.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q) ||
        item.sector.toLowerCase().includes(q) ||
        String(item.rank).includes(q)
    );
  }, [allUniverseDetails, universeSearch]);

  const universeTotalPages = Math.max(1, Math.ceil(filteredUniverse.length / universePageSize));
  const paginatedUniverse = filteredUniverse.slice(
    (universePage - 1) * universePageSize,
    universePage * universePageSize
  );

  React.useEffect(() => {
    setUniversePage(1);
  }, [universeDate, universeSearch]);

  // Auto-select first symbol if none selected
  React.useEffect(() => {
    if (!selectedSymbol && allCoverage.length > 0) {
      setSelectedSymbol(allCoverage[0].symbol);
    }
  }, [allCoverage, selectedSymbol]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
          Data Pipeline & Market Universe
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Ingest OHLCV data, inspect point-in-time universe constituents (NSE 101–750), and verify corporate action adjustments.
        </p>
      </div>

      {/* Ingestion Trigger Card */}
      <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-lg">Ingest Market Data</CardTitle>
            </div>
            <Badge variant="outline" className="text-xs">
              Idempotent Engine
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Trigger ingestion for equities, benchmark index (^NSEI), and constituent history. Existing dates will not be duplicated.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-2">
              <label
                htmlFor="ingest-start"
                className="text-xs font-semibold text-slate-600 dark:text-slate-400"
              >
                Start:
              </label>
              <input
                id="ingest-start"
                type="date"
                data-testid="ingest-start"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
              />
            </div>

            <div className="flex items-center space-x-2">
              <label
                htmlFor="ingest-end"
                className="text-xs font-semibold text-slate-600 dark:text-slate-400"
              >
                End:
              </label>
              <input
                id="ingest-end"
                type="date"
                data-testid="ingest-end"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
              />
            </div>

            <div className="flex items-center space-x-2">
              <label
                htmlFor="ingest-scope"
                className="text-xs font-semibold text-slate-600 dark:text-slate-400"
              >
                Scope:
              </label>
              <select
                id="ingest-scope"
                data-testid="ingest-scope"
                aria-label="Ingestion Scope"
                value={ingestScope}
                onChange={(e) =>
                  setIngestScope(
                    e.target.value as "smoke" | "midcap" | "full" | "custom"
                  )
                }
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
              >
                <option value="smoke">Smoke Test (4 Stocks + Benchmark)</option>
                <option value="midcap">MidCap 150 (NSE Ranks 101–250)</option>
                <option value="full">Full Universe (NSE Ranks 101–750)</option>
                <option value="custom">Custom Symbols</option>
              </select>
            </div>

            {ingestScope === "custom" && (
              <div className="flex items-center space-x-2 flex-1 min-w-[220px]">
                <label
                  htmlFor="custom-symbols-input"
                  className="text-xs font-semibold text-slate-600 dark:text-slate-400 shrink-0"
                >
                  Symbols:
                </label>
                <input
                  id="custom-symbols-input"
                  type="text"
                  data-testid="custom-symbols-input"
                  placeholder="e.g. RELIANCE, TCS, INFY"
                  value={customSymbols}
                  onChange={(e) => setCustomSymbols(e.target.value)}
                  className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono w-full"
                />
              </div>
            )}

            <Button
              data-testid="ingest-button"
              size="sm"
              disabled={ingestMutation.isPending}
              onClick={handleStartIngest}
              className="ml-auto text-xs"
            >
              {ingestMutation.isPending ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Ingesting Data...
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5 mr-1.5" /> Start Ingestion
                </>
              )}
            </Button>
          </div>

          {ingestFeedback && (
            <div
              data-testid="ingest-status-banner"
              className={`p-3 rounded-lg text-xs space-y-1.5 ${
                ingestFeedback.type === "error"
                  ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400 border border-red-200 dark:border-red-900"
                  : ingestFeedback.type === "warning"
                  ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-200 dark:border-amber-900"
                  : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900"
              }`}
            >
              <div className="flex items-center space-x-2">
                {ingestFeedback.type === "error" ? (
                  <AlertTriangle className="w-4 h-4 shrink-0 text-red-600 dark:text-red-400" />
                ) : ingestFeedback.type === "warning" ? (
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                )}
                <span className="font-medium">{ingestFeedback.message}</span>
              </div>
              {ingestFeedback.details && ingestFeedback.details.length > 0 && (
                <ul className="mt-1 pl-6 list-disc text-[11px] space-y-0.5 opacity-90">
                  {ingestFeedback.details.map((detail, idx) => (
                    <li key={idx}>{detail}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Coverage Table Card */}
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <BarChart2 className="w-5 h-5 text-indigo-600" />
                <CardTitle className="text-lg">Stored Data Coverage</CardTitle>
              </div>
              <Badge variant="outline" className="text-xs">
                {allCoverage.length} Symbols
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Sessions stored in database. Click any row to inspect price series.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4 flex-1">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search symbol..."
                aria-label="Filter coverage symbols"
                value={searchFilter}
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full pl-8 pr-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs"
              />
            </div>

            <div
              tabIndex={0}
              role="region"
              aria-label="Stored data coverage table"
              className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden"
            >
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-100 dark:bg-slate-800/60 font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Start Date</th>
                    <th className="py-2.5 px-3">End Date</th>
                    <th className="py-2.5 px-3 text-right">Sessions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                  {coverageQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-600 dark:text-slate-400">
                        <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-blue-600" />
                        Loading coverage data...
                      </td>
                    </tr>
                  ) : paginatedCoverage.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-600 dark:text-slate-400">
                        No coverage found. Run ingestion to populate.
                      </td>
                    </tr>
                  ) : (
                    paginatedCoverage.map((item) => (
                      <tr
                        key={item.symbol}
                        data-testid={`coverage-row-${item.symbol}`}
                        onClick={() => setSelectedSymbol(item.symbol)}
                        className={`cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-900 ${
                          selectedSymbol === item.symbol
                            ? "bg-blue-50/80 dark:bg-blue-950/40 font-medium"
                            : ""
                        }`}
                      >
                        <td className="py-2 px-3 font-mono font-semibold text-blue-600 dark:text-blue-400">
                          {item.symbol}
                        </td>
                        <td className="py-2 px-3 font-mono text-slate-600 dark:text-slate-400">
                          {item.first_date || "—"}
                        </td>
                        <td className="py-2 px-3 font-mono text-slate-600 dark:text-slate-400">
                          {item.last_date || "—"}
                        </td>
                        <td className="py-2 px-3 font-mono text-right font-semibold">
                          {item.rows}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>

          <CardFooter className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 pt-3">
            <span className="text-xs text-slate-600 dark:text-slate-400">
              Page {page} of {totalPages}
            </span>
            <div className="flex items-center space-x-1">
              <Button
                variant="outline"
                size="sm"
                data-testid="coverage-prev"
                aria-label="Previous coverage page"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-7 px-2 text-xs"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                data-testid="coverage-next"
                aria-label="Next coverage page"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="h-7 px-2 text-xs"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </CardFooter>
        </Card>

        {/* Universe Viewer Card */}
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Layers className="w-5 h-5 text-emerald-600" />
                <CardTitle className="text-lg">Universe Explorer</CardTitle>
              </div>
              <Badge variant="outline" className="text-xs">
                NSE 101–750
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Resolve constituent membership ranked 101 to 750 by market cap for any date.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4 flex-1">
            <div className="flex items-center space-x-3">
              <Calendar className="w-4 h-4 text-slate-400" />
              <label
                htmlFor="universe-date-input"
                className="text-xs font-semibold text-slate-600 dark:text-slate-400"
              >
                Evaluation Date:
              </label>
              <input
                id="universe-date-input"
                type="date"
                data-testid="universe-date-input"
                value={universeDate}
                onChange={(e) => setUniverseDate(e.target.value)}
                className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
              />
            </div>

            {universeQuery.data && (
              <div className="space-y-3">
                {/* Bias Indicator */}
                {universeQuery.data.survivorship_bias ? (
                  <div
                    data-testid="universe-bias-badge"
                    className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-xs flex items-center space-x-2"
                  >
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>
                      <strong>⚠️ Survivorship Bias Detected:</strong> Point-in-time constituent file unavailable for {universeDate}. Falling back to current list.
                    </span>
                  </div>
                ) : (
                  <div
                    data-testid="universe-clean-badge"
                    className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-300 text-xs flex items-center space-x-2"
                  >
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>
                      <strong>Point-in-Time Validated:</strong> Exact historical constituents loaded without survivorship bias.
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
                  <span>Constituents Count: <strong>{universeQuery.data.count}</strong></span>
                  <span>Effective Date: <code className="font-mono">{universeQuery.data.date}</code></span>
                </div>

                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    data-testid="universe-search-input"
                    aria-label="Filter universe constituents"
                    placeholder="Search constituent by symbol, name, sector, or rank..."
                    value={universeSearch}
                    onChange={(e) => setUniverseSearch(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs"
                  />
                </div>

                <div
                  tabIndex={0}
                  role="region"
                  aria-label="Universe constituents table"
                  data-testid="universe-tickers"
                  className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden"
                >
                  <table data-testid="universe-table" className="w-full text-xs text-left">
                    <thead className="bg-slate-100 dark:bg-slate-800/60 font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3 w-16">Rank</th>
                        <th className="py-2.5 px-3">Symbol</th>
                        <th className="py-2.5 px-3">Company Name</th>
                        <th className="py-2.5 px-3">Sector</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                      {paginatedUniverse.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-6 text-center text-slate-600 dark:text-slate-400">
                            No constituents match &ldquo;{universeSearch}&rdquo;
                          </td>
                        </tr>
                      ) : (
                        paginatedUniverse.map((item) => (
                          <tr
                            key={item.symbol}
                            data-testid={`universe-row-${item.symbol}`}
                            onClick={() => setSelectedSymbol(item.symbol)}
                            className="hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"
                          >
                            <td className="py-2 px-3 font-mono font-medium text-slate-600 dark:text-slate-400">
                              #{item.rank}
                            </td>
                            <td className="py-2 px-3">
                              <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
                                {item.symbol}
                              </span>
                            </td>
                            <td className="py-2 px-3 font-medium text-slate-900 dark:text-slate-100">
                              <span>{item.name}</span>
                            </td>
                            <td className="py-2 px-3">
                              <Badge variant="secondary" className="text-[10px] font-normal">
                                {item.sector}
                              </Badge>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>

          <CardFooter className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 pt-3">
            <span className="text-xs text-slate-600 dark:text-slate-400">
              Page {universePage} of {universeTotalPages} ({filteredUniverse.length} constituents)
            </span>
            <div className="flex items-center space-x-1">
              <Button
                variant="outline"
                size="sm"
                data-testid="universe-prev"
                aria-label="Previous universe page"
                disabled={universePage <= 1}
                onClick={() => setUniversePage((p) => Math.max(1, p - 1))}
                className="h-7 px-2 text-xs"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                data-testid="universe-next"
                aria-label="Next universe page"
                disabled={universePage >= universeTotalPages}
                onClick={() => setUniversePage((p) => Math.min(universeTotalPages, p + 1))}
                className="h-7 px-2 text-xs"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </CardFooter>
        </Card>
      </div>

      {/* Prices Drilldown Section (Recharts Line Chart) */}
      <Card className="border-slate-200 dark:border-slate-800 shadow-sm" data-testid="prices-drilldown-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <LineChartIcon className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-lg">
                Price Series Drilldown: <span className="text-blue-600">{selectedSymbol}</span>
              </CardTitle>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className="text-xs">
                Close vs. Adj Close
              </Badge>
              {pricesQuery.data && (
                <Badge variant="secondary" className="text-xs">
                  {pricesQuery.data.count} Bars
                </Badge>
              )}
            </div>
          </div>
          <CardDescription className="text-xs">
            Visual inspection of corporate-action adjustments. Divergences demonstrate splits, bonuses, or dividend adjustments.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {pricesQuery.isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-2 text-slate-500">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <p className="text-xs">Loading price series for {selectedSymbol}...</p>
            </div>
          ) : pricesQuery.isError ? (
            <div className="py-12 text-center text-xs text-red-500">
              No prices available for {selectedSymbol}. Ensure data has been ingested.
            </div>
          ) : pricesQuery.data && pricesQuery.data.prices.length > 0 ? (
            <div data-testid="prices-chart" className="w-full h-80 pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={pricesQuery.data.prices}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(val) => val.slice(0, 7)}
                    minTickGap={40}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(val) => `₹${val}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15, 23, 42, 0.9)",
                      borderRadius: "0.5rem",
                      borderColor: "#334155",
                      fontSize: "12px",
                      color: "#f8fafc",
                    }}
                    formatter={(val: number) => [`₹${val.toFixed(2)}`, ""]}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  <Line
                    type="monotone"
                    dataKey="close"
                    name="Unadjusted Close"
                    stroke="#94a3b8"
                    strokeWidth={1.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="adj_close"
                    name="Adjusted Close"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-slate-600 dark:text-slate-400">
              No data available. Click Ingest above.
            </div>
          )}
        </CardContent>

        <CardFooter className="border-t border-slate-100 dark:border-slate-800 pt-3 text-xs text-slate-600 dark:text-slate-400 flex justify-between">
          <span>All moving average indicators in Phase 2 are calculated on Adjusted Close.</span>
          <span>Dates strictly enforced $\le D$ (No Look-Ahead)</span>
        </CardFooter>
      </Card>
    </div>
  );
}
