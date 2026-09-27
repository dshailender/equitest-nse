import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import ReportsHubPage from "@/app/reports/page";
import { server } from "./setup";

describe("ReportsHubPage Component (/reports)", () => {
  it("renders backtest runs list from MSW with stats and table", async () => {
    render(<ReportsHubPage />);

    // Assert initial loading indicator
    expect(screen.getByTestId("reports-loading")).toBeInTheDocument();

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByTestId("stat-total-runs")).toHaveTextContent("1");
    });

    expect(screen.getByTestId("stat-completed-runs")).toHaveTextContent("1");
    expect(screen.getByTestId("row-report-test-run-123")).toBeInTheDocument();

    // Verify Latest Simulation Card
    expect(screen.getByTestId("btn-view-latest-report")).toBeInTheDocument();
    expect(
      screen.getByTestId("btn-view-latest-report").closest("a")
    ).toHaveAttribute("href", "/reports/test-run-123");

    // Verify row button link
    const viewBtn = screen.getByTestId("btn-view-test-run-123");
    expect(viewBtn).toBeInTheDocument();
    expect(viewBtn.closest("a")).toHaveAttribute("href", "/reports/test-run-123");
  });

  it("renders empty state when no historical backtest runs exist", async () => {
    server.use(
      http.get("*/api/v1/backtest", () => {
        return HttpResponse.json([]);
      })
    );

    render(<ReportsHubPage />);

    await waitFor(() => {
      expect(screen.getByTestId("reports-empty")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/No Backtest Reports Found/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Launch Backtest Engine/i).closest("a")
    ).toHaveAttribute("href", "/backtest");
  });

  it("renders error state when fetch fails and allows retry", async () => {
    let callCount = 0;
    server.use(
      http.get("*/api/v1/backtest", () => {
        callCount++;
        if (callCount === 1) {
          return new HttpResponse(null, { status: 500 });
        }
        return HttpResponse.json([
          {
            run_id: "retry-run-456",
            status: "completed",
            created_at: "2026-09-24T12:00:00Z",
            start_date: "2021-01-01",
            end_date: "2022-01-01",
            initial_capital: 500000.0,
            final_capital: 550000.0,
            total_return_pct: 0.10,
            total_trades: 15,
            win_rate: 0.60,
            max_drawdown_pct: 0.04,
            cagr: 0.10,
            error_message: null,
          },
        ]);
      })
    );

    render(<ReportsHubPage />);

    await waitFor(() => {
      expect(screen.getByTestId("reports-error")).toBeInTheDocument();
    });

    expect(screen.getByText(/Failed to Load Reports/i)).toBeInTheDocument();

    // Click retry
    const retryBtn = screen.getByRole("button", { name: /Retry Loading/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByTestId("row-report-retry-run-456")).toBeInTheDocument();
    });
  });

  it("handles refresh button click", async () => {
    render(<ReportsHubPage />);

    await waitFor(() => {
      expect(screen.getByTestId("table-reports-list")).toBeInTheDocument();
    });

    const refreshBtn = screen.getByTestId("btn-refresh-reports");
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(screen.getByTestId("table-reports-list")).toBeInTheDocument();
    });
  });
});
