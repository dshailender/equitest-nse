import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ValidationPage from "../app/validation/page";

describe("ValidationPage Component (REQ-8.1)", () => {
  it("renders page header, control inputs, and stats cards", async () => {
    render(<ValidationPage />);

    expect(
      screen.getByText("TradingView Cross-Check Verification")
    ).toBeInTheDocument();
    expect(screen.getByTestId("run-select")).toBeInTheDocument();
    expect(screen.getByTestId("symbol-input")).toHaveValue("BALKRISIND");
    expect(screen.getByTestId("btn-download-tv")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("stat-sessions")).toHaveTextContent("3");
    });
    expect(screen.getByTestId("stat-entries")).toHaveTextContent("1");
    expect(screen.getByTestId("stat-exits")).toHaveTextContent("1");
  });

  it("renders cross-check table with indicators and signal badges", async () => {
    render(<ValidationPage />);

    await waitFor(() => {
      expect(screen.queryAllByTestId("cross-check-row").length).toBe(3);
    });

    const rows = screen.getAllByTestId("cross-check-row");
    expect(rows.length).toBe(3);


    // Verify presence of signal badges
    expect(screen.getByTestId("badge-entry")).toHaveTextContent("ENTRY");
    expect(screen.getByTestId("badge-exit")).toHaveTextContent("EXIT");
  });

  it("filters table when 'Show only sessions with Entry / Exit signals' is toggled", async () => {
    render(<ValidationPage />);

    await waitFor(() => {
      expect(screen.queryAllByTestId("cross-check-row").length).toBe(3);
    });

    const toggle = screen.getByTestId("toggle-signals-only");
    fireEvent.click(toggle);

    // 2 rows have signals (1 entry, 1 exit)
    expect(screen.getAllByTestId("cross-check-row").length).toBe(2);
  });

  it("triggers file download on clicking 'Download for TradingView Diff'", async () => {
    render(<ValidationPage />);

    await waitFor(() => {
      expect(screen.getByTestId("btn-download-tv")).not.toBeDisabled();
    });

    const clickSpy = vi.fn();
    const origCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const el = origCreateElement(tagName);
      if (tagName === "a") {
        el.click = clickSpy;
      }
      return el;
    });

    const downloadBtn = screen.getByTestId("btn-download-tv");
    fireEvent.click(downloadBtn);

    expect(clickSpy).toHaveBeenCalled();
  });

  it("uses active universe constituents (ranks 101-750) and excludes large-caps (AUD-C-001)", async () => {
    render(<ValidationPage />);
    const input = screen.getByTestId("symbol-input");
    expect(input).toHaveValue("BALKRISIND");

    // Assert quick-select buttons contain only authentic midcap constituents
    const quickSelectButtons = ["BALKRISIND", "FEDERALBNK", "TATAELXSI", "AUBANK", "ASHOKLEY"];
    for (const sym of quickSelectButtons) {
      expect(screen.getByRole("button", { name: sym })).toBeInTheDocument();
    }

    // Assert large caps and synthetic tokens are excluded from quick-select buttons
    const largeCaps = ["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS", "ALPHA"];
    for (const sym of largeCaps) {
      expect(screen.queryByRole("button", { name: sym })).not.toBeInTheDocument();
    }
  });
});
