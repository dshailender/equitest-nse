"use client";

import React, { useEffect, useState } from "react";
import { Check, Copy, FileCode, GitCommit, HardDrive, Layers, ShieldCheck } from "lucide-react";
import { type BacktestAuditResponse, fetchBacktestAudit } from "../lib/api";

interface AuditPanelProps {
  runId: string;
}

export function AuditPanel({ runId }: AuditPanelProps) {
  const [audit, setAudit] = useState<BacktestAuditResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedSha, setCopiedSha] = useState<boolean>(false);
  const [showConfig, setShowConfig] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    async function loadAudit() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchBacktestAudit(runId);
        if (isMounted) setAudit(data);
      } catch (err: unknown) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load audit record");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    if (runId) {
      loadAudit();
    }
    return () => {
      isMounted = false;
    };
  }, [runId]);

  const copySha = () => {
    if (!audit?.git_sha) return;
    navigator.clipboard.writeText(audit.git_sha);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  if (loading) {
    return (
      <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm animate-pulse space-y-3" data-testid="audit-panel">
        <div className="h-5 bg-slate-200 dark:bg-slate-800 rounded w-1/4" />
        <div className="h-4 bg-slate-100 dark:bg-slate-800/60 rounded w-3/4" />
      </div>
    );
  }

  if (error || !audit) {
    return (
      <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm" data-testid="audit-panel">
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <ShieldCheck className="w-4 h-4 text-slate-400" />
          <span>Audit trail unavailable: {error || "No audit record found"}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4" data-testid="audit-panel">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
            Reproducibility & Provenance Audit
          </h3>
        </div>
        {audit.created_at && (
          <span className="text-xs text-slate-500 font-mono">
            Executed: {new Date(audit.created_at).toLocaleString()}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Git SHA */}
        <div className="space-y-1.5">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <GitCommit className="w-3.5 h-3.5" />
            Git Commit SHA
          </span>
          <div className="flex items-center gap-2">
            <code
              data-testid="audit-git-sha"
              className="px-2.5 py-1 text-xs font-mono bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded border border-slate-200 dark:border-slate-700 truncate"
              title={audit.git_sha}
            >
              {audit.git_sha}
            </code>
            <button
              type="button"
              onClick={copySha}
              className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors"
              title="Copy commit hash"
            >
              {copiedSha ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Data Snapshot Hash */}
        <div className="space-y-1.5">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <HardDrive className="w-3.5 h-3.5" />
            Input Parquet SHA-256
          </span>
          <div className="flex items-center gap-2">
            <code
              data-testid="audit-data-hash"
              className="px-2.5 py-1 text-xs font-mono bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded border border-slate-200 dark:border-slate-700 truncate"
              title={audit.data_hash}
            >
              {audit.data_hash}
            </code>
          </div>
        </div>
      </div>

      {/* Library Versions */}
      <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5" />
          Runtime & Library Versions
        </span>
        <div className="flex flex-wrap gap-2" data-testid="audit-versions">
          {Object.entries(audit.versions).map(([lib, ver]) => (
            <span
              key={lib}
              className="px-2 py-0.5 text-xs font-mono bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700"
            >
              <strong className="text-slate-900 dark:text-slate-100 font-semibold">{lib}:</strong> {ver}
            </span>
          ))}
        </div>
      </div>

      {/* Strategy Configuration JSON */}
      <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
        <button
          type="button"
          onClick={() => setShowConfig(!showConfig)}
          className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1.5"
        >
          <FileCode className="w-3.5 h-3.5" />
          {showConfig ? "Hide Strategy Parameters" : "View Strategy Parameters"}
        </button>

        {showConfig && (
          <div className="mt-2" data-testid="audit-config">
            <pre className="p-3 text-xs bg-slate-950 text-slate-200 rounded-lg overflow-x-auto font-mono">
              {JSON.stringify(audit.config, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
