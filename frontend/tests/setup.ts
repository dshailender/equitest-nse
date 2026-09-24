import "@testing-library/jest-dom/vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";

// Mock ResizeObserver for Recharts in jsdom
if (typeof window !== "undefined" && !window.ResizeObserver) {
  const MockResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  (window as unknown as { ResizeObserver: unknown }).ResizeObserver = MockResizeObserver;
  (global as unknown as { ResizeObserver: unknown }).ResizeObserver = MockResizeObserver;
}

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

export const mockIndicators = {
  symbol: "RELIANCE",
  count: 3,
  indicators: [
    {
      date: "2021-06-01",
      open: 750,
      high: 760,
      low: 740,
      close: 750,
      adj_close: 750,
      volume: 20000,
      ema_20: 745.0,
      ema_50: 730.0,
      ema_150: 710.0,
      ema_200: 700.0,
      high_52w: 780.0,
      indicators: { ema_20: 745.0, ema_50: 730.0, ema_150: 710.0, ema_200: 700.0, high_52w: 780.0 },
    },
    {
      date: "2021-06-02",
      open: 755,
      high: 765,
      low: 750,
      close: 760,
      adj_close: 760,
      volume: 15000,
      ema_20: 746.5,
      ema_50: 731.2,
      ema_150: 710.8,
      ema_200: 700.6,
      high_52w: 780.0,
      indicators: { ema_20: 746.5, ema_50: 731.2, ema_150: 710.8, ema_200: 700.6, high_52w: 780.0 },
    },
    {
      date: "2021-06-03",
      open: 762,
      high: 770,
      low: 758,
      close: 768,
      adj_close: 768,
      volume: 18000,
      ema_20: 748.5,
      ema_50: 732.6,
      ema_150: 711.5,
      ema_200: 701.3,
      high_52w: 780.0,
      indicators: { ema_20: 748.5, ema_50: 732.6, ema_150: 711.5, ema_200: 701.3, high_52w: 780.0 },
    },
  ],
};

export const mockSignals = [
  {
    date: "2020-06-23",
    open: 450.0,
    high: 455.0,
    low: 448.0,
    close: 452.0,
    adj_close: 452.0,
    volume: 10000,
    ema_20: 455.0,
    ema_50: 440.0,
    ema_150: 420.0,
    ema_200: 400.0,
    high_52w: 480.0,
    regime_ok: true,
    trend_ok: true,
    near_52w_high: true,
    crossover: false,
    entry: false,
    exit: true,
  },
  {
    date: "2020-06-24",
    open: 453.0,
    high: 456.0,
    low: 450.0,
    close: 454.0,
    adj_close: 454.0,
    volume: 12000,
    ema_20: 455.0,
    ema_50: 441.0,
    ema_150: 421.0,
    ema_200: 401.0,
    high_52w: 480.0,
    regime_ok: true,
    trend_ok: true,
    near_52w_high: true,
    crossover: false,
    entry: false,
    exit: true,
  },
  {
    date: "2020-06-25",
    open: 456.0,
    high: 465.0,
    low: 455.0,
    close: 462.0,
    adj_close: 462.0,
    volume: 25000,
    ema_20: 456.0,
    ema_50: 442.0,
    ema_150: 422.0,
    ema_200: 402.0,
    high_52w: 480.0,
    regime_ok: true,
    trend_ok: true,
    near_52w_high: true,
    crossover: true,
    entry: true,
    exit: false,
  },
  {
    date: "2020-06-26",
    open: 463.0,
    high: 468.0,
    low: 460.0,
    close: 464.0,
    adj_close: 464.0,
    volume: 18000,
    ema_20: 457.0,
    ema_50: 443.0,
    ema_150: 423.0,
    ema_200: 403.0,
    high_52w: 480.0,
    regime_ok: true,
    trend_ok: true,
    near_52w_high: true,
    crossover: false,
    entry: false,
    exit: false,
  },
];

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

  // Indicators - Nifty
  http.get("*/api/v1/indicators/nifty", () => {
    return HttpResponse.json({
      ...mockIndicators,
      symbol: "NIFTY50",
    });
  }),

  // Indicators - Symbol
  http.get("*/api/v1/indicators/:symbol", ({ params, request }) => {
    const url = new URL(request.url);
    const start = url.searchParams.get("start");
    const end = url.searchParams.get("end");
    // Return mockIndicators with the queried symbol and echo start/end if filtered
    return HttpResponse.json({
      ...mockIndicators,
      symbol: (params.symbol as string).toUpperCase(),
      query_start: start,
      query_end: end,
    });
  }),

  // Indicators - Preview
  http.post("*/api/v1/indicators/preview", async ({ request }) => {
    const body = (await request.json()) as { symbol?: string };
    return HttpResponse.json({
      ...mockIndicators,
      symbol: body.symbol || "RELIANCE",
    });
  }),

  // Signals - Screen
  http.get("*/api/v1/signals/screen", () => {
    return HttpResponse.json({
      date: "2020-06-25",
      count: 1,
      symbols: ["MIDCAP_STOCK_101"],
      survivorship_bias: false,
    });
  }),

  // Signals - Symbol
  http.get("*/api/v1/signals/:symbol", ({ params }) => {
    return HttpResponse.json({
      symbol: (params.symbol as string).toUpperCase(),
      count: mockSignals.length,
      signals: mockSignals,
    });
  }),

  // Risk - Config
  http.get("*/api/v1/risk/config", () => {
    return HttpResponse.json({
      corpus: 500000.0,
      risk_pct: 0.02,
      stop_loss_pct: 0.07,
      lot_size: 1,
      cost_bps: 10.0,
    });
  }),

  // Risk - Size
  http.post("*/api/v1/risk/size", async ({ request }) => {
    const body = (await request.json()) as {
      corpus: number;
      entry: number;
      sl_pct?: number;
      risk_pct?: number;
      lot_size?: number;
    };
    const slPct = body.sl_pct ?? 0.07;
    const riskPct = body.risk_pct ?? 0.02;
    const lotSize = body.lot_size ?? 1;

    const riskAmt = Math.round(body.corpus * riskPct * 100) / 100;
    const slDist = body.entry * slPct;
    const rawQty = riskAmt / slDist;
    const qty = Math.floor(rawQty / lotSize) * lotSize;
    const capital = Math.round(qty * body.entry * 100) / 100;
    const slPrice = Math.round(body.entry * (1 - slPct) * 100) / 100;

    return HttpResponse.json({
      qty,
      capital_required: capital,
      sl_price: slPrice,
      risk_amount: riskAmt,
    });
  }),

  // Backtest - Run Trigger
  http.post("*/api/v1/backtest/run", () => {
    return HttpResponse.json(
      {
        run_id: "test-run-123",
        status: "pending",
        message: "Backtest execution queued successfully",
      },
      { status: 202 }
    );
  }),

  // Backtest - Trigger Sweep
  http.post("*/api/v1/backtest/sweep", () => {
    return HttpResponse.json(
      {
        sweep_id: "test-sweep-123",
        total_runs: 4,
        run_ids: ["run-1", "run-2", "run-3", "run-4"],
        status: "pending",
        message: "Parameter sweep execution queued successfully",
      },
      { status: 202 }
    );
  }),

  // Backtest - Sweep Status
  http.get("*/api/v1/backtest/sweep/:sweep_id", ({ params }) => {
    return HttpResponse.json({
      sweep_id: params.sweep_id,
      status: "completed",
      created_at: "2026-09-24T12:00:00Z",
      param_grid: { sl_pct: [0.05, 0.07], risk_pct: [0.01, 0.02] },
      total_runs: 4,
      completed_runs: 4,
      runs: [
        {
          run_id: "run-1",
          status: "completed",
          params: { sl_pct: 0.05, risk_pct: 0.01 },
          initial_capital: 500000.0,
          final_capital: 512000.0,
          total_return_pct: 0.024,
          cagr: 0.012,
          total_trades: 4,
          win_rate: 0.5,
          max_drawdown_pct: 0.02,
          error_message: null,
        },
        {
          run_id: "run-2",
          status: "completed",
          params: { sl_pct: 0.05, risk_pct: 0.02 },
          initial_capital: 500000.0,
          final_capital: 525000.0,
          total_return_pct: 0.05,
          cagr: 0.025,
          total_trades: 4,
          win_rate: 0.5,
          max_drawdown_pct: 0.035,
          error_message: null,
        },
        {
          run_id: "run-3",
          status: "completed",
          params: { sl_pct: 0.07, risk_pct: 0.01 },
          initial_capital: 500000.0,
          final_capital: 495000.0,
          total_return_pct: -0.01,
          cagr: -0.005,
          total_trades: 2,
          win_rate: 0.0,
          max_drawdown_pct: 0.02,
          error_message: null,
        },
        {
          run_id: "run-4",
          status: "completed",
          params: { sl_pct: 0.07, risk_pct: 0.02 },
          initial_capital: 500000.0,
          final_capital: 482707.2,
          total_return_pct: -0.0346,
          cagr: -0.0175,
          total_trades: 2,
          win_rate: 0.0,
          max_drawdown_pct: 0.0383,
          error_message: null,
        },
      ],
    });
  }),

  // Backtest - Compare
  http.get("*/api/v1/backtest/compare", ({ request }) => {
    const url = new URL(request.url);
    const runIdsParam = url.searchParams.get("run_ids") || "run-1,run-2";
    const runIds = runIdsParam.split(",").map((s) => s.trim());

    const runsMap: Record<string, unknown> = {};
    const curvesMap: Record<string, unknown[]> = {};

    runIds.forEach((id, idx) => {
      const finalCap = idx === 0 ? 512000.0 : 482707.2;
      runsMap[id] = {
        run_id: id,
        status: "completed",
        config: { sl_pct: 0.05 + idx * 0.02, risk_pct: 0.01 + idx * 0.01 },
        initial_capital: 500000.0,
        final_capital: finalCap,
        total_return_pct: idx === 0 ? 0.024 : -0.0346,
        cagr: idx === 0 ? 0.012 : -0.0175,
        total_trades: idx === 0 ? 4 : 2,
        win_rate: idx === 0 ? 0.5 : 0.0,
        max_drawdown_pct: idx === 0 ? 0.02 : 0.0383,
        avg_profit: 2000.0,
        avg_loss: -1000.0,
      };
      curvesMap[id] = [
        {
          date: "2020-06-01",
          equity: 500000.0,
          cash: 500000.0,
          positions_value: 0.0,
          open_positions: 0,
          daily_return: 0.0,
          drawdown: 0.0,
          drawdown_pct: 0.0,
        },
        {
          date: "2022-04-29",
          equity: finalCap,
          cash: finalCap,
          positions_value: 0.0,
          open_positions: 0,
          daily_return: 0.0,
          drawdown: 5000.0,
          drawdown_pct: 0.01,
        },
      ];
    });

    return HttpResponse.json({
      run_ids: runIds,
      runs: runsMap,
      equity_curves: curvesMap,
    });
  }),

  // Backtest - Status
  http.get("*/api/v1/backtest/:run_id", ({ params }) => {
    return HttpResponse.json({
      run_id: params.run_id,
      status: "completed",
      created_at: "2026-09-24T12:00:00Z",
      start_date: "2020-06-01",
      end_date: "2022-04-29",
      initial_capital: 500000.0,
      final_capital: 482707.2,
      total_return_pct: -0.0346,
      total_trades: 2,
      win_rate: 0.0,
      error_message: null,
    });
  }),

  // Backtest - Trades
  http.get("*/api/v1/backtest/:run_id/trades", ({ params }) => {
    return HttpResponse.json({
      run_id: params.run_id,
      count: 2,
      trades: [
        {
          symbol: "ALPHA",
          entry_date: "2021-05-25",
          entry_price: 217.83,
          qty: 656,
          exit_date: "2021-08-10",
          exit_price: 194.42,
          pnl: -15356.96,
          pnl_pct: -0.1075,
          exit_reason: "gap",
          days_held: 55,
          costs: 268.96,
        },
        {
          symbol: "ALPHA",
          entry_date: "2021-11-02",
          entry_price: 211.83,
          qty: 654,
          exit_date: "2022-02-23",
          exit_price: 208.87,
          pnl: -1935.84,
          pnl_pct: -0.014,
          exit_reason: "exit_signal",
          days_held: 81,
          costs: 274.68,
        },
      ],
    });
  }),

  // Backtest - Equity Curve
  http.get("*/api/v1/backtest/:run_id/equity", ({ params }) => {
    return HttpResponse.json({
      run_id: params.run_id,
      count: 3,
      equity_curve: [
        {
          date: "2020-06-01",
          equity: 500000.0,
          cash: 500000.0,
          positions_value: 0.0,
          open_positions: 0,
          daily_return: 0.0,
          drawdown: 0.0,
          drawdown_pct: 0.0,
        },
        {
          date: "2021-05-25",
          equity: 499800.0,
          cash: 357100.0,
          positions_value: 142700.0,
          open_positions: 1,
          daily_return: -0.0004,
          drawdown: 200.0,
          drawdown_pct: 0.0004,
        },
        {
          date: "2022-04-29",
          equity: 482707.2,
          cash: 482707.2,
          positions_value: 0.0,
          open_positions: 0,
          daily_return: 0.0,
          drawdown: 19208.32,
          drawdown_pct: 0.0383,
        },
      ],
    });
  }),

  // Backtest - List Runs
  http.get("*/api/v1/backtest", () => {
    return HttpResponse.json([
      {
        run_id: "test-run-123",
        status: "completed",
        created_at: "2026-09-24T12:00:00Z",
        start_date: "2020-06-01",
        end_date: "2022-04-29",
        initial_capital: 500000.0,
        final_capital: 482707.2,
        total_return_pct: -0.0346,
        total_trades: 2,
        win_rate: 0.0,
        error_message: null,
      },
    ]);
  }),

  // Reports - Summary (REQ-7.1)
  http.get("*/api/v1/reports/:run_id/summary", ({ params }) => {
    return HttpResponse.json({
      run_id: params.run_id,
      status: "completed",
      created_at: "2026-09-24T12:00:00Z",
      config: { capital: 500000.0, sl_pct: 0.07, risk_pct: 0.02 },
      metrics: {
        total_trades: 2,
        win_trades: 0,
        loss_trades: 2,
        win_rate: 0.0,
        avg_profit: 0.0,
        avg_loss: -8646.40,
        total_return_pct: -0.0346,
        initial_capital: 500000.0,
        final_capital: 482707.2,
        net_profit: -17292.80,
        cagr: -0.0183,
        max_drawdown_pct: 0.0383,
        max_drawdown_amount: 19208.32,
        sharpe_ratio: -0.5854,
        sortino_ratio: -0.5859,
        calmar_ratio: -0.4270,
        profit_factor: 0.0,
        expectancy: -8646.40,
        avg_days_held: 68.0,
      },
    });
  }),

  // Reports - Monthly Matrix (REQ-7.2)
  http.get("*/api/v1/reports/:run_id/monthly", ({ params }) => {
    return HttpResponse.json({
      run_id: params.run_id,
      years: [
        {
          year: 2020,
          jan: null,
          feb: null,
          mar: null,
          apr: null,
          may: null,
          jun: 0.0,
          jul: 0.0,
          aug: 0.0,
          sep: 0.0,
          oct: 0.0,
          nov: 0.0,
          dec: 0.0,
          total: 0.0,
        },
        {
          year: 2021,
          jan: 0.0,
          feb: 0.0,
          mar: 0.0,
          apr: 0.0,
          may: 0.0006,
          jun: 0.0014,
          jul: 0.0014,
          aug: -0.0340,
          sep: 0.0,
          oct: 0.0,
          nov: 0.0014,
          dec: 0.0012,
          total: -0.0282,
        },
        {
          year: 2022,
          jan: 0.0011,
          feb: -0.0077,
          mar: 0.0,
          apr: 0.0,
          may: null,
          jun: null,
          jul: null,
          aug: null,
          sep: null,
          oct: null,
          nov: null,
          dec: null,
          total: -0.0066,
        },
      ],
    });
  }),

  // Reports - Export (REQ-7.3)
  http.get("*/api/v1/reports/:run_id/export", ({ request, params }) => {
    const url = new URL(request.url);
    const fmt = url.searchParams.get("format") || "csv";
    if (fmt === "csv") {
      const csv = "symbol,entry_date,entry_price,qty,exit_date,exit_price,pnl,pnl_pct,exit_reason,days_held,costs\nALPHA,2021-05-25,217.83,656,2021-08-10,194.42,-15356.96,-0.1075,gap,55,268.96\nALPHA,2021-11-02,211.83,654,2022-02-23,208.87,-1935.84,-0.014,exit_signal,81,274.68\n";
      return new HttpResponse(csv, {
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition": `attachment; filename="${params.run_id}_trades.csv"`,
        },
      });
    } else if (fmt === "xlsx") {
      return new HttpResponse(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
        headers: {
          "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "Content-Disposition": `attachment; filename="${params.run_id}_report.xlsx"`,
        },
      });
    } else {
      return new HttpResponse(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
        headers: {
          "Content-Type": "application/zip",
          "Content-Disposition": `attachment; filename="${params.run_id}_report.zip"`,
        },
      });
    }
  }),
];

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
