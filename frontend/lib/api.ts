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
export const UniverseResponseSchema = z.object({
  date: z.string(),
  count: z.number(),
  tickers: z.array(z.string()),
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

