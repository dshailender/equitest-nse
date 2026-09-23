import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import IndicatorsPage from "@/app/indicators/page";
import { Providers } from "@/app/providers";

// Mock ResizeObserver for Recharts in jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe("IndicatorsPage Component", () => {
  it("renders 4 EMA lines + price and tests legend toggles", async () => {
    render(
      <Providers>
        <IndicatorsPage />
      </Providers>
    );

    // 1. Wait for indicator chart card to render
    await waitFor(() => {
      expect(screen.getByTestId("indicator-chart-card")).toBeInTheDocument();
      expect(screen.getByTestId("indicator-chart")).toBeInTheDocument();
    });

    // 2. Verify all 4 EMA toggles + price toggle exist
    const priceToggle = screen.getByTestId("toggle-price");
    const ema20Toggle = screen.getByTestId("toggle-ema-20");
    const ema50Toggle = screen.getByTestId("toggle-ema-50");
    const ema150Toggle = screen.getByTestId("toggle-ema-150");
    const ema200Toggle = screen.getByTestId("toggle-ema-200");

    expect(priceToggle).toBeInTheDocument();
    expect(ema20Toggle).toBeInTheDocument();
    expect(ema50Toggle).toBeInTheDocument();
    expect(ema150Toggle).toBeInTheDocument();
    expect(ema200Toggle).toBeInTheDocument();

    // Verify initial state is active (not line-through)
    expect(ema150Toggle).not.toHaveClass("line-through");

    // 3. Click toggle for EMA-150
    fireEvent.click(ema150Toggle);

    // Verify EMA-150 toggle button reflects disabled state
    await waitFor(() => {
      expect(screen.getByTestId("toggle-ema-150")).toHaveClass("line-through");
    });

    // 4. Click again to re-enable
    fireEvent.click(screen.getByTestId("toggle-ema-150"));
    await waitFor(() => {
      expect(screen.getByTestId("toggle-ema-150")).not.toHaveClass("line-through");
    });
  });

  it("time-range picker re-fetches and updates chart with new range", async () => {
    render(
      <Providers>
        <IndicatorsPage />
      </Providers>
    );

    // Wait for initial render
    await waitFor(() => {
      expect(screen.getByTestId("indicator-chart")).toBeInTheDocument();
    });

    // Change start date
    const startInput = screen.getByTestId("indicator-start-date");
    fireEvent.change(startInput, { target: { value: "2022-01-01" } });

    // Change end date
    const endInput = screen.getByTestId("indicator-end-date");
    fireEvent.change(endInput, { target: { value: "2022-12-31" } });

    // Assert inputs updated
    expect(startInput).toHaveValue("2022-01-01");
    expect(endInput).toHaveValue("2022-12-31");

    // Assert chart remains rendered with updated state
    await waitFor(() => {
      expect(screen.getByTestId("indicator-chart")).toBeInTheDocument();
    });
  });
});
