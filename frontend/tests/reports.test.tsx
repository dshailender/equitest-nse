import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ReportDetailPage from "../app/reports/[runId]/page";

describe("Reports & Analytics Dashboard (/reports/[runId])", () => {
  it("renders core and advanced KPI metric cards from MSW", async () => {
    render(<ReportDetailPage params={{ runId: "test-run-123" }} />);

    // Assert initial loading indicator
    expect(
      screen.getByText(/loading report & analytics for test-run-123/i)
    ).toBeInTheDocument();

    // Await report title
    await waitFor(() => {
      expect(
        screen.getByText("Strategy Performance Report")
      ).toBeInTheDocument();
    });

    // Core Metrics
    expect(screen.getByTestId("metric-final-capital")).toHaveTextContent(
      "₹482,707.20"
    );
    expect(screen.getByTestId("metric-total-return")).toHaveTextContent(
      "-3.46%"
    );
    expect(screen.getByTestId("metric-total-trades")).toHaveTextContent("2");
    expect(screen.getByTestId("metric-win-rate")).toHaveTextContent("0.00%");
    expect(screen.getByTestId("metric-avg-profit")).toHaveTextContent("₹0.00");
    expect(screen.getByTestId("metric-avg-loss")).toHaveTextContent("-₹8,646.40");

    // Advanced Metrics
    expect(screen.getByTestId("metric-cagr")).toHaveTextContent("-1.83%");
    expect(screen.getByTestId("metric-max-drawdown")).toHaveTextContent("3.83%");
    expect(screen.getByTestId("metric-sharpe")).toHaveTextContent("-0.5854");
    expect(screen.getByTestId("metric-sortino")).toHaveTextContent("-0.5859");
    expect(screen.getByTestId("metric-calmar")).toHaveTextContent("-0.4270");
    expect(screen.getByTestId("metric-profit-factor")).toHaveTextContent("0.00");
    expect(screen.getByTestId("metric-expectancy")).toHaveTextContent(
      "-₹8,646.40"
    );
    expect(screen.getByTestId("metric-avg-days-held")).toHaveTextContent(
      "68.0d"
    );

    // Benchmark Relative Metrics (AUD-H-001)
    expect(screen.getByTestId("metric-benchmark-return")).toHaveTextContent(
      "15.24%"
    );
    expect(screen.getByTestId("metric-benchmark-cagr")).toHaveTextContent(
      "7.82%"
    );
    expect(screen.getByTestId("metric-alpha")).toHaveTextContent("-4.51%");
    expect(screen.getByTestId("metric-beta")).toHaveTextContent("0.85");
    expect(screen.getByTestId("metric-information-ratio")).toHaveTextContent(
      "-0.62"
    );
  });

  it("renders charts and monthly returns heatmap table", async () => {
    render(<ReportDetailPage params={{ runId: "test-run-123" }} />);

    await waitFor(() => {
      expect(screen.getByTestId("chart-equity-curve")).toBeInTheDocument();
      expect(screen.getByTestId("chart-drawdown")).toBeInTheDocument();
    });

    expect(screen.getByTestId("chart-trade-distribution")).toBeInTheDocument();

    const monthlyTable = screen.getByTestId("table-monthly-returns");
    expect(monthlyTable).toBeInTheDocument();
    expect(screen.getByText("2020")).toBeInTheDocument();
    expect(screen.getByText("2021")).toBeInTheDocument();
    expect(screen.getByText("2022")).toBeInTheDocument();
    expect(screen.getByText("-3.40%")).toBeInTheDocument(); // August 2021 gap loss
  });

  it("triggers file download when export buttons are clicked", async () => {
    render(<ReportDetailPage params={{ runId: "test-run-123" }} />);

    await waitFor(() => {
      expect(screen.getByTestId("btn-export-csv")).toBeInTheDocument();
    });

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click");

    // Click Export CSV
    fireEvent.click(screen.getByTestId("btn-export-csv"));
    expect(clickSpy).toHaveBeenCalled();

    // Click Export Excel
    fireEvent.click(screen.getByTestId("btn-export-xlsx"));
    expect(clickSpy).toHaveBeenCalled();

    // Click Export ZIP
    fireEvent.click(screen.getByTestId("btn-export-zip"));
    expect(clickSpy).toHaveBeenCalled();

    clickSpy.mockRestore();
  });

  it("renders AuditPanel with Git SHA, data snapshot hash, and library versions (REQ-8.2)", async () => {
    render(<ReportDetailPage params={{ runId: "test-run-123" }} />);

    await waitFor(() => {
      expect(screen.getByTestId("audit-panel")).toBeInTheDocument();
    });

    expect(screen.getByTestId("audit-git-sha")).toHaveTextContent(
      "45391fbd9b001161b500a4c5e92a22170daee4b9"
    );
    expect(screen.getByTestId("audit-data-hash")).toBeInTheDocument();
    expect(screen.getByTestId("audit-versions")).toHaveTextContent("python:");
    expect(screen.getByTestId("audit-versions")).toHaveTextContent("pandas:");
  });
});

