import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import RiskPage from "../app/risk/page";

describe("RiskPage Component", () => {
  it("renders form with default values and shows qty matching backend fixture", async () => {
    render(<RiskPage />);

    // Assert inputs are populated with default values
    const corpusInput = screen.getByTestId("input-corpus") as HTMLInputElement;
    const entryInput = screen.getByTestId("input-entry") as HTMLInputElement;
    const slInput = screen.getByTestId("input-sl") as HTMLInputElement;
    const riskInput = screen.getByTestId("input-risk") as HTMLInputElement;

    expect(corpusInput.value).toBe("500000");
    expect(entryInput.value).toBe("100");
    expect(slInput.value).toBe("7");
    expect(riskInput.value).toBe("2");

    // Wait for initial position sizing results to load
    await waitFor(() => {
      const qtyElem = screen.getByTestId("result-qty");
      expect(qtyElem).toHaveTextContent("1,428");
    });

    expect(screen.getByTestId("result-capital")).toHaveTextContent("1,42,800");
    expect(screen.getByTestId("result-sl-price")).toHaveTextContent("93");
    expect(screen.getByTestId("result-risk-amount")).toHaveTextContent("10,000");
  });

  it("updates inputs to 100k corpus and verifies derived values", async () => {
    render(<RiskPage />);

    const corpusInput = screen.getByTestId("input-corpus");
    fireEvent.change(corpusInput, { target: { value: "100000" } });

    const submitBtn = screen.getByTestId("btn-calculate");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      const qtyElem = screen.getByTestId("result-qty");
      expect(qtyElem).toHaveTextContent("285");
    });

    expect(screen.getByTestId("result-capital")).toHaveTextContent("28,500");
    expect(screen.getByTestId("result-risk-amount")).toHaveTextContent("2,000");
  });

  it("validates form inputs and renders field errors for invalid data", async () => {
    render(<RiskPage />);

    const corpusInput = screen.getByTestId("input-corpus");
    fireEvent.change(corpusInput, { target: { value: "-500" } });

    const entryInput = screen.getByTestId("input-entry");
    fireEvent.change(entryInput, { target: { value: "0" } });

    const submitBtn = screen.getByTestId("btn-calculate");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId("error-corpus")).toHaveTextContent(
        "Corpus must be greater than 0"
      );
      expect(screen.getByTestId("error-entry")).toHaveTextContent(
        "Entry price must be greater than 0"
      );
    });
  });
});
