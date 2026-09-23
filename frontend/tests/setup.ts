import "@testing-library/jest-dom/vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";

// Mock fixtures
export const mockCoverageItems = [
  { symbol: "RELIANCE", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
  { symbol: "HDFCBANK", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
  { symbol: "INFY", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
  { symbol: "TATAMOTORS", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
  { symbol: "MIDCAP_101", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
  { symbol: "MIDCAP_102", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
  { symbol: "MIDCAP_103", first_date: "2020-01-01", last_date: "2023-12-31", rows: 1000 },
];

export const mockUniverseClean = {
  date: "2022-01-01",
  count: 650,
  tickers: ["MIDCAP_101", "MIDCAP_102", "MIDCAP_103"],
  survivorship_bias: false,
};

export const mockUniverseBiased = {
  date: "2010-01-01",
  count: 650,
  tickers: ["FALLBACK_101", "FALLBACK_102"],
  survivorship_bias: true,
};

export const mockPrices = {
  symbol: "RELIANCE",
  count: 3,
  prices: [
    { date: "2021-05-31", open: 1500, high: 1510, low: 1490, close: 1500, adj_close: 750, volume: 10000 },
    { date: "2021-06-01", open: 750, high: 760, low: 740, close: 750, adj_close: 750, volume: 20000 },
    { date: "2021-06-02", open: 755, high: 765, low: 750, close: 760, adj_close: 760, volume: 15000 },
  ],
};

export const handlers = [
  // Health
  http.get("http://localhost:8000/health", () => {
    return HttpResponse.json({ status: "ok", version: "0.1.0" });
  }),
  http.get("/health", () => {
    return HttpResponse.json({ status: "ok", version: "0.1.0" });
  }),

  // Coverage
  http.get("*/api/v1/data/coverage", () => {
    return HttpResponse.json({ items: mockCoverageItems });
  }),

  // Ingest
  http.post("*/api/v1/data/ingest", () => {
    return HttpResponse.json({
      job_id: "test-job-uuid-1234",
      status: "completed",
      symbols_ingested: 2,
      rows_ingested: 500,
      errors: [],
    });
  }),

  // Universe
  http.get("*/api/v1/universe", ({ request }) => {
    const url = new URL(request.url);
    const date = url.searchParams.get("date");
    if (date === "2010-01-01") {
      return HttpResponse.json(mockUniverseBiased);
    }
    return HttpResponse.json(mockUniverseClean);
  }),

  // Prices
  http.get("*/api/v1/prices/:symbol", ({ params }) => {
    return HttpResponse.json({
      ...mockPrices,
      symbol: params.symbol,
    });
  }),
];

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
