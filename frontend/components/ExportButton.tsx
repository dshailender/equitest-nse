"use client";

import React, { useEffect, useState } from "react";
import {
  QueryClient,
  QueryClientContext,
  QueryClientProvider,
  useMutation,
} from "@tanstack/react-query";
import {
  fetchPdfJobStatus,
  getPdfJobDownloadUrl,
  getReportExportUrl,
  PdfJobResponseSchema,
} from "@/lib/api";

export interface ExportButtonProps {
  format: "pdf" | "csv" | "xlsx";
  runId: string;
}

interface ToastMessage {
  type: "info" | "error" | "success";
  text: string;
}

const fallbackQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

export function ExportButton(props: ExportButtonProps) {
  const client = React.useContext(QueryClientContext);
  if (!client) {
    return (
      <QueryClientProvider client={fallbackQueryClient}>
        <ExportButtonInner {...props} />
      </QueryClientProvider>
    );
  }
  return <ExportButtonInner {...props} />;
}

function ExportButtonInner({ format, runId }: ExportButtonProps) {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Auto-dismiss toast after 5s if success/error
  useEffect(() => {
    if (!toast || toast.type === "info") return;
    const timer = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(timer);
  }, [toast]);

  // Polling hook for asynchronous 202 job completion (REQ-9.4)
  useEffect(() => {
    if (!activeJobId) return;

    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const job = await fetchPdfJobStatus(activeJobId);
        if (!isMounted) return;

        if (job.status === "ready") {
          clearInterval(interval);
          setActiveJobId(null);
          setToast(null);

          // Trigger download from ready endpoint
          const dlUrl = getPdfJobDownloadUrl(activeJobId);
          const link = document.createElement("a");
          link.href = dlUrl;
          link.download = `backtest_${runId}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        } else if (job.status === "failed") {
          clearInterval(interval);
          setActiveJobId(null);
          setToast({
            type: "error",
            text: job.error || "Asynchronous PDF generation failed.",
          });
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        clearInterval(interval);
        setActiveJobId(null);
        const msg = err instanceof Error ? err.message : "Failed to poll job status.";
        setToast({ type: "error", text: msg });
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeJobId, runId]);

  const mutation = useMutation({
    mutationFn: async () => {
      const url = getReportExportUrl(runId, format);
      const res = await fetch(url);

      if (res.status === 200) {
        const disposition = res.headers.get("Content-Disposition");
        let filename = `backtest_${runId}.${format}`;
        if (disposition) {
          const match = disposition.match(/filename="?([^"]+)"?/);
          if (match && match[1]) {
            filename = match[1];
          }
        }

        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);

        return { status: 200 as const };
      } else if (res.status === 202) {
        const json = await res.json();
        const parsed = PdfJobResponseSchema.pick({ job_id: true }).parse(json);
        return { status: 202 as const, jobId: parsed.job_id };
      } else {
        let errorMsg = `Export failed with status: ${res.status}`;
        try {
          const errData = await res.json();
          if (errData && typeof errData.detail === "string") {
            errorMsg = errData.detail;
          }
        } catch {
          // ignore parse errors
        }
        throw new Error(errorMsg);
      }
    },
    onSuccess: (data) => {
      if (data.status === 202 && data.jobId) {
        setToast({ type: "info", text: "Generating PDF..." });
        setActiveJobId(data.jobId);
      }
    },
    onError: (err: Error) => {
      setToast({ type: "error", text: err.message });
    },
  });

  const isLoading = mutation.isPending || activeJobId !== null;

  const getButtonStyles = () => {
    switch (format) {
      case "pdf":
        return "bg-indigo-600 hover:bg-indigo-700 text-white";
      case "xlsx":
        return "bg-emerald-600 hover:bg-emerald-700 text-white";
      case "csv":
      default:
        return "bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200";
    }
  };

  const getIcon = () => {
    switch (format) {
      case "pdf":
        return "📄";
      case "xlsx":
        return "📊";
      case "csv":
      default:
        return "📥";
    }
  };

  const getLabel = () => {
    if (isLoading) return "Generating...";
    switch (format) {
      case "pdf":
        return "Export PDF";
      case "xlsx":
        return "Export Excel";
      case "csv":
      default:
        return "Export CSV";
    }
  };

  return (
    <>
      <button
        onClick={() => mutation.mutate()}
        disabled={isLoading}
        data-testid={`btn-export-${format}`}
        className={`px-3.5 py-2 text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${getButtonStyles()}`}
      >
        {isLoading ? (
          <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          <span>{getIcon()}</span>
        )}
        <span>{getLabel()}</span>
      </button>

      {/* Floating Toast Notification */}
      {toast && (
        <div
          role="alert"
          data-testid="export-toast"
          className={`fixed bottom-5 right-5 z-50 max-w-sm p-4 rounded-xl shadow-lg border flex items-start space-x-3 transition-all ${
            toast.type === "info"
              ? "bg-slate-900 text-white border-slate-800"
              : toast.type === "error"
              ? "bg-rose-50 text-rose-900 border-rose-200 dark:bg-rose-950 dark:text-rose-100 dark:border-rose-900"
              : "bg-emerald-50 text-emerald-900 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-100 dark:border-emerald-900"
          }`}
        >
          {toast.type === "info" && (
            <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mt-0.5" />
          )}
          {toast.type === "error" && <span className="text-base leading-none">⚠️</span>}
          {toast.type === "success" && <span className="text-base leading-none">✓</span>}
          <div className="flex-1 text-xs font-medium leading-relaxed">{toast.text}</div>
          <button
            onClick={() => setToast(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs font-bold px-1"
            aria-label="Dismiss toast"
          >
            ✕
          </button>
        </div>
      )}
    </>
  );
}
