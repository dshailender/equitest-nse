import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import BacktestPage from "../app/backtest/page";

describe("BacktestPage Component", () => {
  it("renders configuration form with default parameters", async () => {
    render(<BacktestPage />);

    expect(screen.getByText("Backtest Simulation Engine")).toBeInTheDocument();
    expect(screen.getByText("Simulation Parameters")).toBeInTheDocument();
    expect(screen.getByDisplayValue("500000")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2020-06-01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2022-04-29")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Run Backtest/i })
    ).toBeInTheDocument();
  });

  it("triggers backtest execution, polls to completion, and displays summary KPIs and trades table", async () => {
    render(<BacktestPage />);

    const runButton = screen.getByRole("button", { name: /Run Backtest/i });
    fireEvent.click(runButton);

    // Wait for polling to complete and summary cards to populate
    await waitFor(
      () => {
        expect(
          screen.getByTestId("final-capital-value")
        ).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    expect(screen.getByTestId("final-capital-value")).toHaveTextContent(
      "482,707.20"
    );
    expect(screen.getByTestId("total-return-value")).toHaveTextContent(
      "-3.46%"
    );
    expect(screen.getByTestId("total-trades-value")).toHaveTextContent("2");
    expect(screen.getByTestId("win-rate-value")).toHaveTextContent("0.0%");

    // Verify trades table rendered
    const table = screen.getByTestId("trades-table");
    expect(table).toBeInTheDocument();
    expect(within(table).getAllByText("ALPHA").length).toBeGreaterThanOrEqual(1);
    expect(within(table).getByText("Gap Down")).toBeInTheDocument();
    expect(within(table).getByText("Exit Signal")).toBeInTheDocument();
  });
});
