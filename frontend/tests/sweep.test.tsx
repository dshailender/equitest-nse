import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import SweepPage from "../app/sweep/page";

describe("SweepPage Component", () => {
  it("renders configuration form with default parameters and permutation count", async () => {
    render(<SweepPage />);

    expect(screen.getByText("Parameter & Scenario Sweep")).toBeInTheDocument();
    expect(screen.getByText("Dynamic Parameter Grid Builder")).toBeInTheDocument();
    expect(screen.getByTestId("input-start-date")).toHaveValue("2020-06-01");
    expect(screen.getByTestId("input-end-date")).toHaveValue("2022-04-29");
    expect(screen.getByTestId("input-capital")).toHaveValue(500000);

    // Initial 2 params with 2 values each = 4 runs
    expect(screen.getByText("4 runs")).toBeInTheDocument();
    expect(screen.getByTestId("btn-run-sweep")).toBeInTheDocument();
  });

  it("updates permutation count when candidate values are added or removed", async () => {
    render(<SweepPage />);

    // Initially 4 runs (sl_pct: [5, 7], risk_pct: [1, 2])
    expect(screen.getByText("4 runs")).toBeInTheDocument();

    // Find the input to add value for sl_pct (the first input with placeholder "Add value...")
    const addInputs = screen.getAllByPlaceholderText("Add value...");
    const addButtons = screen.getAllByRole("button", { name: "Add" });

    // Add a 3rd value (e.g. "10") to sl_pct
    fireEvent.change(addInputs[0], { target: { value: "10" } });
    fireEvent.click(addButtons[0]);

    // Now 3 values * 2 values = 6 runs
    expect(screen.getByText("6 runs")).toBeInTheDocument();

    // Remove the newly added value "10"
    const valBadge = screen.getByText("10");
    const removeBtn = within(valBadge).getByRole("button", { name: "×" });
    fireEvent.click(removeBtn);

    // Back to 4 runs
    expect(screen.getByText("4 runs")).toBeInTheDocument();
  });

  it("triggers sweep execution, polls to completion, renders 2D heatmap and runs table", async () => {
    render(<SweepPage />);

    const runButton = screen.getByTestId("btn-run-sweep");
    fireEvent.click(runButton);

    // Wait for polling to complete and runs table to populate
    await waitFor(
      () => {
        expect(screen.getByTestId("sweep-runs-table")).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Verify progress banner shows completed
    expect(screen.getByText(/Sweep Status: completed/i)).toBeInTheDocument();
    expect(screen.getByText(/\(4 \/ 4 completed\)/i)).toBeInTheDocument();

    // Verify 2D Heatmap is rendered
    expect(
      screen.getByText(/Sensitivity Heatmap \(CAGR % by sl_pct vs risk_pct\)/i)
    ).toBeInTheDocument();

    // Verify runs table rows
    const table = screen.getByTestId("sweep-runs-table");
    expect(within(table).getByText("run-1")).toBeInTheDocument();
    expect(within(table).getByText("run-2")).toBeInTheDocument();
    expect(within(table).getByText("run-3")).toBeInTheDocument();
    expect(within(table).getByText("run-4")).toBeInTheDocument();
  });

  it("selects runs and opens compare drawer with chart and metrics diff table", async () => {
    render(<SweepPage />);

    const runButton = screen.getByTestId("btn-run-sweep");
    fireEvent.click(runButton);

    await waitFor(
      () => {
        expect(screen.getByTestId("sweep-runs-table")).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Select run-1 and run-2 checkboxes
    const cb1 = screen.getByTestId("checkbox-run-run-1");
    const cb2 = screen.getByTestId("checkbox-run-run-2");
    fireEvent.click(cb1);
    fireEvent.click(cb2);

    // Open Compare Drawer
    const compareBtn = screen.getByTestId("btn-open-compare");
    expect(compareBtn).toHaveTextContent("Compare Selected (2)");
    fireEvent.click(compareBtn);

    // Wait for compare drawer to open and compare chart to render
    await waitFor(
      () => {
        expect(screen.getByTestId("compare-drawer")).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    expect(screen.getByTestId("compare-chart")).toBeInTheDocument();
    expect(
      screen.getByText("Multi-Run Comparison (2 runs)")
    ).toBeInTheDocument();

    // Verify close compare drawer
    const closeBtn = screen.getByTestId("btn-close-compare");
    fireEvent.click(closeBtn);
    expect(screen.queryByTestId("compare-drawer")).not.toBeInTheDocument();
  });
});
