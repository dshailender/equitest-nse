import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "@/app/page";

describe("HomePage Component", () => {
  it("renders institutional branding and value proposition without scaffolding", () => {
    render(<HomePage />);

    // Assert main title includes Backtesting Framework
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toHaveTextContent(/Backtesting Framework/i);
    expect(heading).toHaveTextContent(/NSE 101–750/i);

    // Assert NO Phase 0 scaffolding badges
    expect(screen.queryByText(/Phase 0: Scaffolding/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Phase 1–3/i)).not.toBeInTheDocument();

    // Assert NO health check diagnostics on the homepage
    expect(screen.queryByText(/Open Health Diagnostic/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/:8000\/health/i)).not.toBeInTheDocument();
  });

  it("renders key quantitative research guarantees (invariants)", () => {
    render(<HomePage />);

    expect(screen.getByText("Zero Look-Ahead")).toBeInTheDocument();
    expect(screen.getByText("Survivorship-Free")).toBeInTheDocument();
    expect(screen.getByText("Top 100 Exclusion")).toBeInTheDocument();
    expect(screen.getByText("Gap-Down Realism")).toBeInTheDocument();
  });

  it("renders primary action buttons linking to core engines", () => {
    render(<HomePage />);

    const backtestBtn = screen.getByTestId("btn-home-backtest");
    expect(backtestBtn).toBeInTheDocument();
    expect(backtestBtn.closest("a")).toHaveAttribute("href", "/backtest");

    const sweepBtn = screen.getByTestId("btn-home-sweep");
    expect(sweepBtn).toBeInTheDocument();
    expect(sweepBtn.closest("a")).toHaveAttribute("href", "/sweep");

    const reportsBtn = screen.getByTestId("btn-home-reports");
    expect(reportsBtn).toBeInTheDocument();
    expect(reportsBtn.closest("a")).toHaveAttribute("href", "/reports");

    const docsBtn = screen.getByTestId("btn-home-docs");
    expect(docsBtn).toBeInTheDocument();
    expect(docsBtn.closest("a")).toHaveAttribute("href", "/docs");
  });

  it("renders 4-stage quantitative pipeline and platform subsystems", () => {
    render(<HomePage />);

    // Pipeline stages
    expect(screen.getByText("Universe & Regime")).toBeInTheDocument();
    expect(screen.getByText("4-EMA Stack & Trend")).toBeInTheDocument();
    expect(screen.getByText("Signals & Ranking")).toBeInTheDocument();
    expect(screen.getByText("Risk & Backtest")).toBeInTheDocument();

    // Subsystems
    expect(screen.getByText("Backtest Simulation")).toBeInTheDocument();
    expect(screen.getByText("Parameter Optimization")).toBeInTheDocument();
    expect(screen.getByText("Reports & Analytics")).toBeInTheDocument();
    expect(screen.getByText("Universe & Ingestion")).toBeInTheDocument();
    expect(screen.getByText("Risk & Capital Engine")).toBeInTheDocument();
    expect(screen.getByText("Audit & Validation")).toBeInTheDocument();
  });
});
