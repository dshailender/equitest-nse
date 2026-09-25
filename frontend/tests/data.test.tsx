import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DataStatusPage from "@/app/data/page";
import { Providers } from "@/app/providers";

// Mock ResizeObserver for Recharts in jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe("DataStatusPage Component", () => {
  it("renders coverage table with fixture data and tests pagination", async () => {
    render(
      <Providers>
        <DataStatusPage />
      </Providers>
    );

    // Wait for coverage table to load
    await waitFor(() => {
      expect(screen.getByTestId("coverage-row-RELIANCE")).toBeInTheDocument();
      expect(screen.getByTestId("coverage-row-HDFCBANK")).toBeInTheDocument();
    });

    // Check page 1 displays 5 items
    expect(screen.getByTestId("coverage-row-MIDCAP_101")).toBeInTheDocument();
    expect(screen.queryByTestId("coverage-row-MIDCAP_102")).not.toBeInTheDocument();

    // Click Next Page button
    const nextBtn = screen.getByTestId("coverage-next");
    expect(nextBtn).toBeEnabled();
    fireEvent.click(nextBtn);

    // Page 2 displays MIDCAP_102
    await waitFor(() => {
      expect(screen.getByTestId("coverage-row-MIDCAP_102")).toBeInTheDocument();
      expect(screen.getByTestId("coverage-row-MIDCAP_103")).toBeInTheDocument();
      expect(screen.queryByTestId("coverage-row-RELIANCE")).not.toBeInTheDocument();
    });

    // Click Prev Page button
    const prevBtn = screen.getByTestId("coverage-prev");
    expect(prevBtn).toBeEnabled();
    fireEvent.click(prevBtn);

    await waitFor(() => {
      expect(screen.getByTestId("coverage-row-RELIANCE")).toBeInTheDocument();
    });
  });

  it("shows survivorship bias badge only when bias flag is true", async () => {
    render(
      <Providers>
        <DataStatusPage />
      </Providers>
    );

    // Initial date 2022-01-01 has survivorship_bias: false
    await waitFor(() => {
      expect(screen.getByTestId("universe-clean-badge")).toBeInTheDocument();
      expect(screen.queryByTestId("universe-bias-badge")).not.toBeInTheDocument();
    });

    // Change date to 2010-01-01 (mocked with survivorship_bias: true)
    const dateInput = screen.getByTestId("universe-date-input");
    fireEvent.change(dateInput, { target: { value: "2010-01-01" } });

    // Assert that bias warning badge is rendered
    await waitFor(() => {
      const biasBadge = screen.getByTestId("universe-bias-badge");
      expect(biasBadge).toBeInTheDocument();
      expect(biasBadge).toHaveTextContent(/Survivorship Bias Detected/i);
      expect(screen.queryByTestId("universe-clean-badge")).not.toBeInTheDocument();
    });
  });

  it("renders universe constituents table with company names, search, and pagination (AUD-B-001)", async () => {
    render(
      <Providers>
        <DataStatusPage />
      </Providers>
    );

    // Wait for universe table and constituents
    await waitFor(() => {
      expect(screen.getByTestId("universe-table")).toBeInTheDocument();
      expect(screen.getByTestId("universe-row-MIDCAP_101")).toBeInTheDocument();
    });

    // Check company name, rank, and sector display
    const row1 = screen.getByTestId("universe-row-MIDCAP_101");
    expect(row1).toHaveTextContent("MIDCAP_101");
    expect(row1).toHaveTextContent("Midcap Stock 101 Ltd");
    expect(row1).toHaveTextContent("#101");
    expect(row1).toHaveTextContent("Capital Goods");

    // Search for a specific company name
    const searchInput = screen.getByTestId("universe-search-input");
    fireEvent.change(searchInput, { target: { value: "Stock 102" } });

    await waitFor(() => {
      expect(screen.getByTestId("universe-row-MIDCAP_102")).toBeInTheDocument();
      expect(screen.getByText("Midcap Stock 102 Ltd")).toBeInTheDocument();
      expect(screen.queryByTestId("universe-row-MIDCAP_101")).not.toBeInTheDocument();
    });

    // Clear search filter
    fireEvent.change(searchInput, { target: { value: "" } });
    await waitFor(() => {
      expect(screen.getByTestId("universe-row-MIDCAP_101")).toBeInTheDocument();
    });

    // Check pagination controls exist
    expect(screen.getByTestId("universe-prev")).toBeInTheDocument();
    expect(screen.getByTestId("universe-next")).toBeInTheDocument();
  });
});

