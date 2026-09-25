import { z } from "zod";
import type { components, paths } from "./schema";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Health Schema ---
export const HealthResponseSchema = z.object({
  status: z.string(),
  version: z.string(),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

// --- Ingest Schemas ---
export const IngestRequestSchema = z.object({
  start: z.string(),
  end: z.string(),
  symbols: z.array(z.string()).optional(),
});
export type IngestRequest = z.infer<typeof IngestRequestSchema>;

export const IngestResponseSchema = z.object({
  job_id: z.string(),
  status: z.string(),
  symbols_ingested: z.number(),
  rows_ingested: z.number(),
  errors: z.array(z.string()).default([]),
});
export type IngestResponse = z.infer<typeof IngestResponseSchema>;

// --- Coverage Schemas ---
export const CoverageItemSchema = z.object({
  symbol: z.string(),
  first_date: z.string().nullable().optional(),
  last_date: z.string().nullable().optional(),
  rows: z.number(),
});
export type CoverageItem = z.infer<typeof CoverageItemSchema>;

export const CoverageResponseSchema = z.object({
  items: z.array(CoverageItemSchema),
});
export type CoverageResponse = z.infer<typeof CoverageResponseSchema>;

// --- Universe Schemas ---
export const ConstituentDetailSchema = z.object({
  symbol: z.string(),
  name: z.string(),
  rank: z.number(),
  sector: z.string().default("Diversified"),
});
export type ConstituentDetail = z.infer<typeof ConstituentDetailSchema>;

export const UniverseResponseSchema = z.object({
  date: z.string(),
  count: z.number(),
  tickers: z.array(z.string()),
  details: z.array(ConstituentDetailSchema).default([]),
  survivorship_bias: z.boolean(),
});
export type UniverseResponse = z.infer<typeof UniverseResponseSchema>;

// --- Price Schemas ---
export const PriceItemSchema = z.object({
  date: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  adj_close: z.number(),
  volume: z.number(),
});
export type PriceItem = z.infer<typeof PriceItemSchema>;

export const PricesResponseSchema = z.object({
  symbol: z.string(),
  count: z.number(),
  prices: z.array(PriceItemSchema),
});
export type PricesResponse = z.infer<typeof PricesResponseSchema>;

// OpenAPI types
export type OpenAPISchemas = components["schemas"];

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Fetch health status from backend /health endpoint
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/health`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `API Health check failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return HealthResponseSchema.parse(json);
}

/**
 * Trigger data ingestion job
 */
export async function triggerIngest(
  start: string,
  end: string,
  symbols?: string[]
): Promise<IngestResponse> {
  const url = `${API_BASE_URL}/api/v1/data/ingest`;
  const body: IngestRequest = { start, end, symbols };

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Data ingestion trigger failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return IngestResponseSchema.parse(json);
}

/**
 * Fetch dataset coverage across all stored symbols
 */
export async function fetchCoverage(): Promise<CoverageResponse> {
  const url = `${API_BASE_URL}/api/v1/data/coverage`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Coverage fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return CoverageResponseSchema.parse(json);
}

/**
 * Fetch universe constituents for a given date
 */
export async function fetchUniverse(date?: string): Promise<UniverseResponse> {
  const query = date ? `?date=${encodeURIComponent(date)}` : "";
  const url = `${API_BASE_URL}/api/v1/universe${query}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Universe fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return UniverseResponseSchema.parse(json);
}

/**
 * Fetch OHLCV prices for a specific symbol
 */
export async function fetchPrices(
  symbol: string,
  start?: string,
  end?: string
): Promise<PricesResponse> {
  const params = new URLSearchParams();
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const url = `${API_BASE_URL}/api/v1/prices/${encodeURIComponent(symbol)}${qs}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Prices fetch failed for ${symbol} with status: ${response.status}`
    );
  }

  const json = await response.json();
  return PricesResponseSchema.parse(json);
}

// --- Indicator Schemas ---
export const IndicatorItemSchema = z.object({
  date: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  adj_close: z.number(),
  volume: z.number(),
  ema_20: z.number().nullable().optional(),
  ema_50: z.number().nullable().optional(),
  ema_150: z.number().nullable().optional(),
  ema_200: z.number().nullable().optional(),
  high_52w: z.number().nullable().optional(),
  indicators: z.record(z.string(), z.number().nullable()).optional().default({}),
});
export type IndicatorItem = z.infer<typeof IndicatorItemSchema>;

export const IndicatorResponseSchema = z.object({
  symbol: z.string(),
  count: z.number(),
  indicators: z.array(IndicatorItemSchema),
});
export type IndicatorResponse = z.infer<typeof IndicatorResponseSchema>;

export const IndicatorConfigSchema = z.object({
  spans: z.array(z.number()).default([20, 50, 150, 200]),
  include_high_52w: z.boolean().default(true),
  high_52w_lookback: z.number().default(252),
});
export type IndicatorConfig = z.infer<typeof IndicatorConfigSchema>;

export const IndicatorPreviewRequestSchema = z.object({
  symbol: z.string().default("RELIANCE"),
  start: z.string().optional().nullable(),
  end: z.string().optional().nullable(),
  config: IndicatorConfigSchema.optional().default({
    spans: [20, 50, 150, 200],
    include_high_52w: true,
    high_52w_lookback: 252,
  }),
});
export type IndicatorPreviewRequest = z.infer<typeof IndicatorPreviewRequestSchema>;

/**
 * Fetch technical indicators for a specific symbol
 */
export async function fetchIndicators(
  symbol: string,
  start?: string,
  end?: string,
  spans?: number[]
): Promise<IndicatorResponse> {
  const params = new URLSearchParams();
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  if (spans && spans.length > 0) params.append("spans", spans.join(","));
  const qs = params.toString() ? `?${params.toString()}` : "";

  const url = `${API_BASE_URL}/api/v1/indicators/${encodeURIComponent(symbol)}${qs}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Indicators fetch failed for ${symbol} with status: ${response.status}`
    );
  }

  const json = await response.json();
  return IndicatorResponseSchema.parse(json);
}

/**
 * Fetch NIFTY benchmark indicators
 */
export async function fetchNiftyIndicators(
  start?: string,
  end?: string,
  spans?: number[]
): Promise<IndicatorResponse> {
  const params = new URLSearchParams();
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  if (spans && spans.length > 0) params.append("spans", spans.join(","));
  const qs = params.toString() ? `?${params.toString()}` : "";

  const url = `${API_BASE_URL}/api/v1/indicators/nifty${qs}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `NIFTY indicators fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return IndicatorResponseSchema.parse(json);
}

/**
 * Preview custom technical indicators
 */
export async function previewIndicators(
  req: IndicatorPreviewRequest
): Promise<IndicatorResponse> {
  const url = `${API_BASE_URL}/api/v1/indicators/preview`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Indicators preview failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return IndicatorResponseSchema.parse(json);
}

// --- Signals Schemas ---
export const SignalItemSchema = z.object({
  date: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  adj_close: z.number(),
  volume: z.number(),
  ema_20: z.number().nullable().optional(),
  ema_50: z.number().nullable().optional(),
  ema_150: z.number().nullable().optional(),
  ema_200: z.number().nullable().optional(),
  high_52w: z.number().nullable().optional(),
  regime_ok: z.boolean(),
  trend_ok: z.boolean(),
  near_52w_high: z.boolean(),
  crossover: z.boolean(),
  entry: z.boolean(),
  exit: z.boolean(),
});
export type SignalItem = z.infer<typeof SignalItemSchema>;

export const SignalsResponseSchema = z.object({
  symbol: z.string(),
  count: z.number(),
  signals: z.array(SignalItemSchema),
});
export type SignalsResponse = z.infer<typeof SignalsResponseSchema>;

export const ScreenResponseSchema = z.object({
  date: z.string(),
  count: z.number(),
  symbols: z.array(z.string()),
  survivorship_bias: z.boolean(),
});
export type ScreenResponse = z.infer<typeof ScreenResponseSchema>;

/**
 * Fetch trading signals and component filter evaluations for a symbol
 */
export async function fetchSignals(
  symbol: string,
  start?: string,
  end?: string
): Promise<SignalsResponse> {
  const params = new URLSearchParams();
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const url = `${API_BASE_URL}/api/v1/signals/${encodeURIComponent(symbol)}${qs}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Signals fetch failed for ${symbol} with status: ${response.status}`
    );
  }

  const json = await response.json();
  return SignalsResponseSchema.parse(json);
}

/**
 * Screen universe constituents for active entry signals on a date
 */
export async function screenUniverse(date: string): Promise<ScreenResponse> {
  const url = `${API_BASE_URL}/api/v1/signals/screen?date=${encodeURIComponent(date)}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Screening failed for date ${date} with status: ${response.status}`
    );
  }

  const json = await response.json();
  return ScreenResponseSchema.parse(json);
}

// --- Risk Schemas ---
export const RiskSizeRequestSchema = z.object({
  corpus: z.number().positive("Corpus must be greater than 0"),
  entry: z.number().positive("Entry price must be greater than 0"),
  sl_pct: z.number().positive("Stop loss must be greater than 0").max(1, "Stop loss fraction must not exceed 1").default(0.07),
  risk_pct: z.number().positive("Risk must be greater than 0").max(1, "Risk fraction must not exceed 1").default(0.02),
  lot_size: z.number().int().min(1, "Lot size must be at least 1").default(1),
});
export type RiskSizeRequest = z.infer<typeof RiskSizeRequestSchema>;

export const RiskSizeResponseSchema = z.object({
  qty: z.number().int(),
  capital_required: z.number(),
  sl_price: z.number(),
  risk_amount: z.number(),
});
export type RiskSizeResponse = z.infer<typeof RiskSizeResponseSchema>;

export const RiskConfigResponseSchema = z.object({
  corpus: z.number(),
  risk_pct: z.number(),
  stop_loss_pct: z.number(),
  lot_size: z.number().int(),
  cost_bps: z.number(),
});
export type RiskConfigResponse = z.infer<typeof RiskConfigResponseSchema>;

/**
 * Calculate position size and risk metrics
 */
export async function calculateRiskSize(
  req: RiskSizeRequest
): Promise<RiskSizeResponse> {
  const url = `${API_BASE_URL}/api/v1/risk/size`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Risk size calculation failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return RiskSizeResponseSchema.parse(json);
}

/**
 * Fetch default risk and execution configuration parameters
 */
export async function fetchRiskConfig(): Promise<RiskConfigResponse> {
  const url = `${API_BASE_URL}/api/v1/risk/config`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Risk config fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return RiskConfigResponseSchema.parse(json);
}

// --- Backtest Schemas ---
export const BacktestConfigSchema = z.object({
  corpus: z.number().default(500000.0),
  capital: z.number().optional().nullable(),
  risk_pct: z.number().default(0.02),
  stop_loss_pct: z.number().default(0.07),
  sl_pct: z.number().optional().nullable(),
  lot_size: z.number().default(1),
  cost_bps: z.number().default(10.0),
  ema_spans: z.array(z.number()).default([20, 50, 150, 200]),
  regime_spans: z.array(z.number()).default([50, 200]),
  high_52w_factor: z.number().default(0.85),
  high_52w_lookback: z.number().default(252),
  allow_crossover_equal: z.boolean().default(false),
  ranking_rule: z.string().default("momentum"),
  universe_start_rank: z.number().default(101),
  universe_end_rank: z.number().default(750),
});
export type BacktestConfig = z.infer<typeof BacktestConfigSchema>;

export const BacktestRunRequestSchema = z.object({
  start: z.string().optional().nullable(),
  end: z.string().optional().nullable(),
  config: BacktestConfigSchema.partial().optional().nullable(),
  symbols: z.array(z.string()).optional().nullable(),
});
export type BacktestRunRequest = z.infer<typeof BacktestRunRequestSchema>;

export const BacktestRunCreateResponseSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  message: z.string(),
});
export type BacktestRunCreateResponse = z.infer<
  typeof BacktestRunCreateResponseSchema
>;

export const BacktestStatusResponseSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  created_at: z.string(),
  start_date: z.string().optional().nullable(),
  end_date: z.string().optional().nullable(),
  config_version: z.string().default("1.0"),
  sweep_id: z.string().optional().nullable(),
  initial_capital: z.number(),
  final_capital: z.number().optional().nullable(),
  total_return_pct: z.number().optional().nullable(),
  cagr: z.number().optional().nullable(),
  total_trades: z.number().optional().nullable(),
  win_rate: z.number().optional().nullable(),
  max_drawdown_pct: z.number().optional().nullable(),
  error_message: z.string().optional().nullable(),
});
export type BacktestStatusResponse = z.infer<
  typeof BacktestStatusResponseSchema
>;

export const SweepRunRequestSchema = z.object({
  base_config: BacktestConfigSchema.partial().optional().nullable(),
  param_grid: z.record(z.array(z.any())),
  start: z.string().optional().nullable(),
  end: z.string().optional().nullable(),
  symbols: z.array(z.string()).optional().nullable(),
});
export type SweepRunRequest = z.infer<typeof SweepRunRequestSchema>;

export const SweepRunCreateResponseSchema = z.object({
  sweep_id: z.string(),
  total_runs: z.number(),
  run_ids: z.array(z.string()),
  status: z.string(),
  message: z.string(),
});
export type SweepRunCreateResponse = z.infer<
  typeof SweepRunCreateResponseSchema
>;

export const SweepRunItemSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  params: z.record(z.any()),
  initial_capital: z.number(),
  final_capital: z.number().optional().nullable(),
  total_return_pct: z.number().optional().nullable(),
  cagr: z.number().optional().nullable(),
  total_trades: z.number().optional().nullable(),
  win_rate: z.number().optional().nullable(),
  max_drawdown_pct: z.number().optional().nullable(),
  error_message: z.string().optional().nullable(),
});
export type SweepRunItem = z.infer<typeof SweepRunItemSchema>;

export const SweepStatusResponseSchema = z.object({
  sweep_id: z.string(),
  status: z.string(),
  created_at: z.string(),
  param_grid: z.record(z.array(z.any())),
  total_runs: z.number(),
  completed_runs: z.number(),
  runs: z.array(SweepRunItemSchema),
});
export type SweepStatusResponse = z.infer<typeof SweepStatusResponseSchema>;

export const CompareMetricItemSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  config: z.record(z.any()),
  initial_capital: z.number(),
  final_capital: z.number().optional().nullable(),
  total_return_pct: z.number().optional().nullable(),
  cagr: z.number().optional().nullable(),
  total_trades: z.number().optional().nullable(),
  win_rate: z.number().optional().nullable(),
  max_drawdown_pct: z.number().optional().nullable(),
  avg_profit: z.number().optional().nullable(),
  avg_loss: z.number().optional().nullable(),
});
export type CompareMetricItem = z.infer<typeof CompareMetricItemSchema>;

export const BacktestCompareResponseSchema = z.object({
  run_ids: z.array(z.string()),
  runs: z.record(CompareMetricItemSchema),
  equity_curves: z.record(z.array(z.lazy(() => EquityPointSchema))),
});
export type BacktestCompareResponse = z.infer<
  typeof BacktestCompareResponseSchema
>;

export const TradeItemSchema = z.object({
  symbol: z.string(),
  entry_date: z.string(),
  entry_price: z.number(),
  qty: z.number(),
  exit_date: z.string(),
  exit_price: z.number(),
  pnl: z.number(),
  pnl_pct: z.number(),
  exit_reason: z.string(),
  days_held: z.number(),
  costs: z.number(),
});
export type TradeItem = z.infer<typeof TradeItemSchema>;

export const BacktestTradesResponseSchema = z.object({
  run_id: z.string(),
  count: z.number(),
  trades: z.array(TradeItemSchema),
});
export type BacktestTradesResponse = z.infer<
  typeof BacktestTradesResponseSchema
>;

export const EquityPointSchema = z.object({
  date: z.string(),
  equity: z.number(),
  cash: z.number(),
  positions_value: z.number(),
  open_positions: z.number(),
  daily_return: z.number(),
  drawdown: z.number(),
  drawdown_pct: z.number(),
});
export type EquityPoint = z.infer<typeof EquityPointSchema>;

export const BacktestEquityResponseSchema = z.object({
  run_id: z.string(),
  count: z.number(),
  equity_curve: z.array(EquityPointSchema),
});
export type BacktestEquityResponse = z.infer<
  typeof BacktestEquityResponseSchema
>;

/**
 * Triggers a backtest execution run asynchronously
 */
export async function runBacktest(
  req: BacktestRunRequest
): Promise<BacktestRunCreateResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/run`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest run trigger failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return BacktestRunCreateResponseSchema.parse(json);
}

/**
 * Fetches status and summary KPIs for a backtest run
 */
export async function fetchBacktestStatus(
  runId: string
): Promise<BacktestStatusResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/${encodeURIComponent(runId)}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest status fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return BacktestStatusResponseSchema.parse(json);
}

/**
 * Fetches trade ledger for a completed backtest run
 */
export async function fetchBacktestTrades(
  runId: string
): Promise<BacktestTradesResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/${encodeURIComponent(runId)}/trades`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest trades fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return BacktestTradesResponseSchema.parse(json);
}

/**
 * Fetches equity curve time series for a completed backtest run
 */
export async function fetchBacktestEquity(
  runId: string
): Promise<BacktestEquityResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/${encodeURIComponent(runId)}/equity`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest equity fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return BacktestEquityResponseSchema.parse(json);
}

/**
 * Fetches list of all previous backtest runs
 */
export async function fetchBacktestRuns(): Promise<BacktestStatusResponse[]> {
  const url = `${API_BASE_URL}/api/v1/backtest`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest runs list fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return z.array(BacktestStatusResponseSchema).parse(json);
}

/**
 * Triggers a parameter grid sweep asynchronously (REQ-6.2)
 */
export async function runSweep(
  req: SweepRunRequest
): Promise<SweepRunCreateResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/sweep`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Sweep run trigger failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return SweepRunCreateResponseSchema.parse(json);
}

/**
 * Fetches status and child run metrics for a parameter sweep (REQ-6.2)
 */
export async function fetchSweepStatus(
  sweepId: string
): Promise<SweepStatusResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/sweep/${encodeURIComponent(sweepId)}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Sweep status fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return SweepStatusResponseSchema.parse(json);
}

/**
 * Compares multiple backtest runs and retrieves aligned metrics and overlaid curves (REQ-6.3)
 */
export async function compareBacktestRuns(
  runIds: string[]
): Promise<BacktestCompareResponse> {
  const params = new URLSearchParams({ run_ids: runIds.join(",") });
  const url = `${API_BASE_URL}/api/v1/backtest/compare?${params.toString()}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest compare fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return BacktestCompareResponseSchema.parse(json);
}

// --- Report & Analytics Schemas (REQ-7.1, REQ-7.2, REQ-7.3) ---

export const PerformanceMetricsSchema = z.object({
  total_trades: z.number(),
  win_trades: z.number(),
  loss_trades: z.number(),
  win_rate: z.number(),
  avg_profit: z.number(),
  avg_loss: z.number(),
  total_return_pct: z.number(),
  initial_capital: z.number(),
  final_capital: z.number(),
  net_profit: z.number(),
  cagr: z.number(),
  max_drawdown_pct: z.number(),
  max_drawdown_amount: z.number(),
  sharpe_ratio: z.number(),
  sortino_ratio: z.number(),
  calmar_ratio: z.number(),
  profit_factor: z.number(),
  expectancy: z.number(),
  avg_days_held: z.number(),
});
export type PerformanceMetrics = z.infer<typeof PerformanceMetricsSchema>;

export const ReportSummaryResponseSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  created_at: z.string(),
  config: z.record(z.unknown()).default({}),
  metrics: PerformanceMetricsSchema,
});
export type ReportSummaryResponse = z.infer<typeof ReportSummaryResponseSchema>;

export const MonthlyReturnRowSchema = z.object({
  year: z.number(),
  jan: z.number().nullable().optional(),
  feb: z.number().nullable().optional(),
  mar: z.number().nullable().optional(),
  apr: z.number().nullable().optional(),
  may: z.number().nullable().optional(),
  jun: z.number().nullable().optional(),
  jul: z.number().nullable().optional(),
  aug: z.number().nullable().optional(),
  sep: z.number().nullable().optional(),
  oct: z.number().nullable().optional(),
  nov: z.number().nullable().optional(),
  dec: z.number().nullable().optional(),
  total: z.number(),
});
export type MonthlyReturnRow = z.infer<typeof MonthlyReturnRowSchema>;

export const ReportMonthlyResponseSchema = z.object({
  run_id: z.string(),
  years: z.array(MonthlyReturnRowSchema),
});
export type ReportMonthlyResponse = z.infer<typeof ReportMonthlyResponseSchema>;

/**
 * Fetches core and advanced performance summary metrics for a backtest run (REQ-7.1)
 */
export async function fetchReportSummary(
  runId: string
): Promise<ReportSummaryResponse> {
  const url = `${API_BASE_URL}/api/v1/reports/${encodeURIComponent(runId)}/summary`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Report summary fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return ReportSummaryResponseSchema.parse(json);
}

/**
 * Fetches Month x Year compounded returns matrix for a backtest run (REQ-7.2)
 */
export async function fetchReportMonthly(
  runId: string
): Promise<ReportMonthlyResponse> {
  const url = `${API_BASE_URL}/api/v1/reports/${encodeURIComponent(runId)}/monthly`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Report monthly fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return ReportMonthlyResponseSchema.parse(json);
}

/**
 * Returns absolute download URL for a backtest report export format (REQ-7.3)
 */
export function getReportExportUrl(
  runId: string,
  format: "csv" | "xlsx" | "zip" | "pdf" = "csv"
): string {
  return `${API_BASE_URL}/api/v1/reports/${encodeURIComponent(runId)}/export?format=${format}`;
}

// --- PDF Async Job Schemas & Methods (REQ-9.4) ---
export const PdfJobResponseSchema = z.object({
  job_id: z.string(),
  status: z.enum(["pending", "ready", "failed"]),
  file_path: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
  created_at: z.string(),
});
export type PdfJobResponse = z.infer<typeof PdfJobResponseSchema>;

export async function fetchPdfJobStatus(jobId: string): Promise<PdfJobResponse> {
  const url = `${API_BASE_URL}/api/v1/reports/jobs/${encodeURIComponent(jobId)}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(
      response.status,
      `PDF job status fetch failed with status: ${response.status}`
    );
  }
  const json = await response.json();
  return PdfJobResponseSchema.parse(json);
}

export function getPdfJobDownloadUrl(jobId: string): string {
  return `${API_BASE_URL}/api/v1/reports/jobs/${encodeURIComponent(jobId)}/download`;
}

// --- Validation Cross-Check Schemas & Methods (REQ-8.1) ---

export const CrossCheckPointSchema = z.object({
  date: z.string(),
  close: z.number(),
  ema_20: z.number().nullable().optional(),
  ema_50: z.number().nullable().optional(),
  ema_150: z.number().nullable().optional(),
  ema_200: z.number().nullable().optional(),
  high_52w: z.number().nullable().optional(),
  entry: z.boolean(),
  exit: z.boolean(),
});
export type CrossCheckPoint = z.infer<typeof CrossCheckPointSchema>;

export const CrossCheckResponseSchema = z.object({
  run_id: z.string(),
  symbol: z.string(),
  count: z.number(),
  rows: z.array(CrossCheckPointSchema),
  csv: z.string(),
});
export type CrossCheckResponse = z.infer<typeof CrossCheckResponseSchema>;

/**
 * Fetches aligned indicator and signal series for TradingView visual cross-check (REQ-8.1)
 */
export async function fetchCrossCheck(
  runId: string,
  symbol: string
): Promise<CrossCheckResponse> {
  const url = `${API_BASE_URL}/api/v1/validation/${encodeURIComponent(
    runId
  )}/${encodeURIComponent(symbol)}?format=json`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Cross-check fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return CrossCheckResponseSchema.parse(json);
}

/**
 * Returns direct CSV download URL for TradingView diff (REQ-8.1)
 */
export function getCrossCheckDownloadUrl(runId: string, symbol: string): string {
  return `${API_BASE_URL}/api/v1/validation/${encodeURIComponent(
    runId
  )}/${encodeURIComponent(symbol)}?format=csv`;
}

// --- Backtest Audit Schemas & Methods (REQ-8.2) ---

export const BacktestAuditResponseSchema = z.object({
  run_id: z.string(),
  git_sha: z.string(),
  config: z.record(z.any()),
  data_hash: z.string(),
  versions: z.record(z.string()),
  created_at: z.string().nullable().optional(),
});
export type BacktestAuditResponse = z.infer<typeof BacktestAuditResponseSchema>;

/**
 * Fetches reproducibility and provenance audit trail for a backtest run (REQ-8.2)
 */
export async function fetchBacktestAudit(
  runId: string
): Promise<BacktestAuditResponse> {
  const url = `${API_BASE_URL}/api/v1/backtest/${encodeURIComponent(
    runId
  )}/audit`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `Backtest audit fetch failed with status: ${response.status}`
    );
  }

  const json = await response.json();
  return BacktestAuditResponseSchema.parse(json);
}







