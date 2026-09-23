import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ApiHealthPage from "@/app/api-health/page";
import { Providers } from "@/app/providers";

describe("ApiHealthPage Component", () => {
  it("renders backend health status and asserts ok and version 0.1.0", async () => {
    render(
      <Providers>
        <ApiHealthPage />
      </Providers>
    );

    // Initial loading indicator
    expect(screen.getByText(/Connecting to backend service/i)).toBeInTheDocument();

    // Wait for MSW mocked response to load and assert "ok"
    await waitFor(() => {
      const statusElement = screen.getByTestId("health-status");
      expect(statusElement).toBeInTheDocument();
      expect(statusElement).toHaveTextContent("ok");
    });

    // Assert version is rendered
    const versionElement = screen.getByTestId("health-version");
    expect(versionElement).toBeInTheDocument();
    expect(versionElement).toHaveTextContent("0.1.0");

    // Assert badge indicates Operational
    expect(screen.getByTestId("health-badge-ok")).toBeInTheDocument();
  });
});
