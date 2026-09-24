import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi, beforeAll } from "vitest";
import { ExportButton } from "../components/ExportButton";
import { server } from "./setup";

describe("ExportButton Component", () => {
  beforeAll(() => {
    if (!window.URL.createObjectURL) {
      window.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    }
    if (!window.URL.revokeObjectURL) {
      window.URL.revokeObjectURL = vi.fn();
    }
  });

  it("triggers synchronous download on 200 binary response", async () => {
    server.use(
      http.get("*/api/v1/reports/:runId/export", ({ request }) => {
        const url = new URL(request.url);
        const format = url.searchParams.get("format");
        if (format === "pdf") {
          return new HttpResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
            status: 200,
            headers: {
              "Content-Type": "application/pdf",
              "Content-Disposition": 'attachment; filename="backtest_test-run.pdf"',
            },
          });
        }
        return new HttpResponse("ok", { status: 200 });
      })
    );

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(<ExportButton format="pdf" runId="test-run" />);

    const btn = screen.getByTestId("btn-export-pdf");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("Export PDF");

    fireEvent.click(btn);

    await waitFor(() => {
      expect(clickSpy).toHaveBeenCalled();
    });

    clickSpy.mockRestore();
  });

  it("handles asynchronous 202 response, polls status, and auto-downloads when ready", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    let pollCount = 0;
    server.use(
      http.get("*/api/v1/reports/:runId/export", () => {
        return HttpResponse.json(
          { job_id: "test-job-999" },
          {
            status: 202,
            headers: { Location: "/api/v1/reports/jobs/test-job-999" },
          }
        );
      }),
      http.get("*/api/v1/reports/jobs/:jobId", () => {
        pollCount += 1;
        if (pollCount <= 1) {
          return HttpResponse.json({
            job_id: "test-job-999",
            status: "pending",
            file_path: null,
            error: null,
            created_at: new Date().toISOString(),
          });
        }
        return HttpResponse.json({
          job_id: "test-job-999",
          status: "ready",
          file_path: "/tmp/report.pdf",
          error: null,
          created_at: new Date().toISOString(),
        });
      }),
      http.get("*/api/v1/reports/jobs/:jobId/download", () => {
        return new HttpResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
          status: 200,
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="backtest_async.pdf"',
          },
        });
      })
    );

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(<ExportButton format="pdf" runId="test-run-large" />);

    fireEvent.click(screen.getByTestId("btn-export-pdf"));

    // Toast "Generating PDF..." should appear
    await vi.waitFor(() => {
      expect(screen.getByTestId("export-toast")).toBeInTheDocument();
      expect(screen.getByText(/Generating PDF\.\.\./i)).toBeInTheDocument();
    });

    // Advance fake timers by 2.5s twice to allow polling cycles
    await vi.advanceTimersByTimeAsync(2500);
    await vi.advanceTimersByTimeAsync(2500);

    // After poll finishes with ready, auto-download should be triggered
    await vi.waitFor(() => {
      expect(clickSpy).toHaveBeenCalled();
    });

    clickSpy.mockRestore();
    vi.useRealTimers();
  });

  it("displays error toast on server 500 failure", async () => {
    server.use(
      http.get("*/api/v1/reports/:runId/export", () => {
        return HttpResponse.json(
          { detail: "Internal error generating PDF bundle" },
          { status: 500 }
        );
      })
    );

    render(<ExportButton format="pdf" runId="test-run-fail" />);

    fireEvent.click(screen.getByTestId("btn-export-pdf"));

    await waitFor(() => {
      expect(screen.getByTestId("export-toast")).toBeInTheDocument();
      expect(
        screen.getByText(/Internal error generating PDF bundle/i)
      ).toBeInTheDocument();
    });
  });
});
