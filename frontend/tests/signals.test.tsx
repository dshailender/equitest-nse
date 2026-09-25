import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SignalsPage from "../app/signals/page";

describe("SignalsPage Component", () => {
  it("renders table with fixture data and asserts entry and exit badges", async () => {
    render(<SignalsPage />);

    // Wait for table to load
    await waitFor(() => {
      expect(screen.getByTestId("signals-table")).toBeInTheDocument();
    });

    // Check table rows
    const rows = screen.getAllByTestId("signal-row");
    expect(rows.length).toBe(4);

    // Assert entry badge exists (for 2020-06-25)
    const entryBadges = screen.getAllByTestId("entry-badge");
    expect(entryBadges.length).toBe(1);
    expect(entryBadges[0]).toHaveTextContent("BUY / ENTRY");

    // Assert exit badges exist (for 2020-06-23, 2020-06-24)
    const exitBadges = screen.getAllByTestId("exit-badge");
    expect(exitBadges.length).toBe(2);
    expect(exitBadges[0]).toHaveTextContent("SELL / EXIT");
  });

  it("toggles 'Only Entries' filter to display only entry rows", async () => {
    render(<SignalsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("signals-table")).toBeInTheDocument();
    });

    // Initially 4 rows
    expect(screen.getAllByTestId("signal-row").length).toBe(4);

    // Toggle Only Entries checkbox
    const toggle = screen.getByTestId("only-entries-toggle");
    fireEvent.click(toggle);

    // After toggle, only 1 row should be rendered
    await waitFor(() => {
      const filteredRows = screen.getAllByTestId("signal-row");
      expect(filteredRows.length).toBe(1);
      expect(filteredRows[0]).toHaveTextContent("2020-06-25");
      expect(screen.getByTestId("entry-badge")).toBeInTheDocument();
      expect(screen.queryByTestId("exit-badge")).not.toBeInTheDocument();
    });
  });

  it("runs universe screen and displays screened ticker", async () => {
    render(<SignalsPage />);

    const screenBtn = screen.getByTestId("screen-button");
    fireEvent.click(screenBtn);

    await waitFor(() => {
      expect(screen.getByTestId("screen-results-card")).toBeInTheDocument();
      expect(screen.getByTestId("screened-symbols-list")).toHaveTextContent(
        "MIDCAP_STOCK_101"
      );
    });
  });

  it("preset symbols contain only active universe constituents (ranks 101-750) and exclude large-caps (AUD-C-001)", async () => {
    render(<SignalsPage />);

    const symbolSelect = screen.getByTestId("signal-symbol-select") as HTMLSelectElement;
    expect(symbolSelect.value).toBe("BALKRISIND");

    const optionValues = Array.from(symbolSelect.options).map((opt) => opt.value);
    expect(optionValues).toEqual([
      "BALKRISIND",
      "FEDERALBNK",
      "TATAELXSI",
      "AUBANK",
      "ASHOKLEY",
    ]);

    // Assert large caps are excluded
    const largeCaps = ["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS"];
    for (const sym of largeCaps) {
      expect(optionValues).not.toContain(sym);
    }
  });
});

