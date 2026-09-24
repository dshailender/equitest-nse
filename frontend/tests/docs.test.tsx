import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DocsPage from "@/app/docs/page";
import { Providers } from "@/app/providers";

describe("DocsPage Component", () => {
  it("renders docs header and default overview content", () => {
    render(
      <Providers>
        <DocsPage />
      </Providers>
    );

    expect(screen.getByTestId("docs-page")).toBeInTheDocument();
    expect(screen.getByText(/EquiTest NSE Documentation & Knowledge Base/i)).toBeInTheDocument();
    expect(screen.getByText(/Clone to Execution in < 15 Minutes/i)).toBeInTheDocument();
    expect(screen.getByText(/Zero Look-Ahead Guarantee/i)).toBeInTheDocument();
  });

  it("switches tabs and displays respective content", () => {
    render(
      <Providers>
        <DocsPage />
      </Providers>
    );

    // Click Architecture tab
    fireEvent.click(screen.getByTestId("tab-architecture"));
    expect(screen.getByText(/System Architecture & Monorepo Boundaries/i)).toBeInTheDocument();
    expect(screen.getByText(/Backend Subsystems/i)).toBeInTheDocument();

    // Click Strategy tab
    fireEvent.click(screen.getByTestId("tab-strategy"));
    expect(screen.getByText(/Quantitative Strategy Rules/i)).toBeInTheDocument();
    expect(screen.getByText(/1. Market Regime Filter/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Stock Trend Filter/i)).toBeInTheDocument();

    // Click Assumptions tab
    fireEvent.click(screen.getByTestId("tab-assumptions"));
    expect(screen.getByTestId("content-assumptions")).toBeInTheDocument();
    expect(screen.getByText(/Open Question #1: Universe Boundaries & Top 100 Exclusion/i)).toBeInTheDocument();
    expect(screen.getByText(/Open Question #2: Overnight Gap-Down Stop-Loss Resolution/i)).toBeInTheDocument();

    // Click Runbook tab
    fireEvent.click(screen.getByTestId("tab-runbook"));
    expect(screen.getByText(/How to Change a Strategy Parameter Walkthrough/i)).toBeInTheDocument();
    expect(screen.getByText(/Update Backend Schema:/i)).toBeInTheDocument();

    // Switch back to Overview
    fireEvent.click(screen.getByTestId("tab-overview"));
    expect(screen.getByText(/System Overview & Quickstart/i)).toBeInTheDocument();
  });
});
