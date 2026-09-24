"use client";

import React, { useState } from "react";
import { BookOpen, Code2, Compass, Cpu, FileQuestion, HelpCircle, Layers, Terminal } from "lucide-react";

type TabKey = "overview" | "architecture" | "strategy" | "assumptions" | "runbook";

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  return (
    <div className="space-y-6" data-testid="docs-page">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            EquiTest NSE Documentation & Knowledge Base
          </h1>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Complete engineering specifications, mathematical definitions, PRD §4 design decisions, and operational guides.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab("overview")}
          data-testid="tab-overview"
          className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "overview"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          Overview & Quickstart
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("architecture")}
          data-testid="tab-architecture"
          className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "architecture"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          Architecture & Design
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("strategy")}
          data-testid="tab-strategy"
          className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "strategy"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          Strategy Rules (PRD §2)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("assumptions")}
          data-testid="tab-assumptions"
          className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "assumptions"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <FileQuestion className="w-3.5 h-3.5" />
          Assumptions & Open Questions
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("runbook")}
          data-testid="tab-runbook"
          className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "runbook"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          Parameter Guide & Runbook
        </button>
      </div>

      {/* Tab Content Display */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm" data-testid="doc-content">
        {/* 1. Overview */}
        {activeTab === "overview" && (
          <div className="space-y-6 prose dark:prose-invert max-w-none text-slate-800 dark:text-slate-200 text-sm leading-relaxed">
            <h2 className="text-xl font-bold tracking-tight">System Overview & Quickstart</h2>
            <p>
              EquiTest NSE is an institutional-grade, event-driven quantitative backtesting platform built specifically for Indian equities (NSE 101–750 constituents). It provides an automated, reproducible research environment combining high-performance vectorized indicator processing, realistic transaction friction and overnight gap modeling, multi-parameter Cartesian grid sweeps, empyrical cross-validated analytics, and direct TradingView visual diff tooling.
            </p>

            <div className="p-4 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 rounded-lg not-prose">
              <h3 className="font-semibold text-blue-900 dark:text-blue-300 text-sm mb-1">Clone to Execution in &lt; 15 Minutes</h3>
              <pre className="p-3 bg-slate-950 text-slate-200 rounded text-xs font-mono mt-2 overflow-x-auto">
{`git clone https://github.com/equitest/equitest-nse.git
cd equitest-nse
make install
make dev`}
              </pre>
            </div>

            <h3 className="text-base font-bold">Key Architectural Invariants</h3>
            <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
              <li><strong>Zero Look-Ahead Guarantee:</strong> Indicators evaluated on session $T$ close; trades executed at session $T+1$ Market Open. Rolling 52W high is strictly shifted by 1 bar.</li>
              <li><strong>Survivorship Bias Prevention:</strong> Resolved using point-in-time constituent records (ranks 101–750). Fallbacks explicitly tagged with <code>survivorship_bias: true</code>.</li>
              <li><strong>Top 100 Large-Cap Exclusion:</strong> Large-cap stocks (ranks 1–100) are explicitly excluded from the trading universe; NIFTY 50 serves solely as an external regime filter.</li>
              <li><strong>Overnight Gap Realism:</strong> Stop loss orders gap-down below the 7% threshold execute at Market Open price, recording actual market drawdown without price improvement.</li>
            </ul>
          </div>
        )}

        {/* 2. Architecture */}
        {activeTab === "architecture" && (
          <div className="space-y-6 text-slate-800 dark:text-slate-200 text-sm leading-relaxed">
            <h2 className="text-xl font-bold tracking-tight">System Architecture & Monorepo Boundaries</h2>
            <p>
              The platform is architected as a modular monorepo cleanly decoupling the vectorized mathematical engine from the presentation layer via OpenAPI 3.1 contracts.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
              <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                <span className="font-semibold text-xs uppercase tracking-wider text-blue-600 dark:text-blue-400">Backend Subsystems</span>
                <ul className="mt-2 text-xs space-y-1 text-slate-600 dark:text-slate-300">
                  <li>• <strong>app/data:</strong> Ingestion, caching, and universe selection</li>
                  <li>• <strong>app/indicators:</strong> Vectorized EMAs and 52W rolling high</li>
                  <li>• <strong>app/strategy:</strong> Trend, regime, 52W proximity, and crossover filters</li>
                  <li>• <strong>app/risk:</strong> Position sizing, overnight gap-down, slippage friction</li>
                  <li>• <strong>app/engine:</strong> Event-driven state machine, momentum ranking, capital constraints</li>
                  <li>• <strong>app/reports:</strong> Empyrical cross-validated metrics, XLSX/ZIP exports</li>
                  <li>• <strong>app/validation:</strong> TradingView cross-check & provenance audit</li>
                </ul>
              </div>

              <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                <span className="font-semibold text-xs uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Frontend Subsystems</span>
                <ul className="mt-2 text-xs space-y-1 text-slate-600 dark:text-slate-300">
                  <li>• <strong>app/data:</strong> Coverage inspection and historical price chart</li>
                  <li>• <strong>app/indicators:</strong> Multi-span EMA overlays and interactive preview</li>
                  <li>• <strong>app/signals:</strong> Universe screener and filter diagnostics</li>
                  <li>• <strong>app/risk:</strong> Position sizing and capital calculator</li>
                  <li>• <strong>app/backtest:</strong> Simulation runner, KPIs, and trade ledger</li>
                  <li>• <strong>app/sweep:</strong> 2D Cartesian heatmap and multi-run comparator</li>
                  <li>• <strong>app/reports/[runId]:</strong> Drawdown chart, return distribution, monthly matrix</li>
                  <li>• <strong>app/validation:</strong> TradingView diff table and CSV generator</li>
                </ul>
              </div>
            </div>

            <div className="p-4 bg-slate-950 text-slate-200 rounded-lg overflow-x-auto font-mono text-xs">
              <pre>{`Data Sources (Parquet / SQLite)
    │
    ▼
Indicators Pipeline ───► Signal Engine ───► Backtest Simulation Engine
                                                    │
                                                    ▼
Audit Log & Parquet Fingerprint ◄──── Results Storage (dev.db & JSON Blobs)
                                                    │
                                                    ▼
                                          Reporting & Analytics`}</pre>
            </div>
          </div>
        )}

        {/* 3. Strategy Rules */}
        {activeTab === "strategy" && (
          <div className="space-y-6 text-slate-800 dark:text-slate-200 text-sm leading-relaxed">
            <h2 className="text-xl font-bold tracking-tight">Quantitative Strategy Rules (Verbatim from PRD §2)</h2>

            <div className="space-y-4">
              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">1. Market Regime Filter</h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-mono">
                  NIFTY Close &gt; EMA 50 AND NIFTY Close &gt; EMA 200
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Evaluated on benchmark closing price. If False on session $T$, zero new trades are entered across the entire universe.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">2. Stock Trend Filter</h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-mono">
                  EMA 20 &gt; EMA 50 &gt; EMA 150 &gt; EMA 200
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Evaluated on stock adjusted close. All 4 EMAs must be strictly stacked in ascending order.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">3. 52-Week High Proximity Filter</h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-mono">
                  Stock Close &gt; 0.85 * 52-Week Rolling High
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Stock price must be within 15% of its 252-day rolling peak (excluding current bar).
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">4. Entry Crossover Trigger & Execution</h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-mono">
                  Close[T] &gt; EMA20[T] AND Close[T-1] &lt; EMA20[T-1]
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Triggered on session $T$ close. Order executes on session $T+1$ Market Open with 10 bps slippage.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">5. Risk Allocation & Sizing</h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-mono">
                  Quantity = floor( (Corpus * 0.02) / (Entry * 0.07) )
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Fixed 2% portfolio risk. Stop loss fixed at 7% below execution entry price.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 4. Assumptions & Open Questions */}
        {activeTab === "assumptions" && (
          <div className="space-y-6 text-slate-800 dark:text-slate-200 text-sm leading-relaxed" data-testid="content-assumptions">
            <h2 className="text-xl font-bold tracking-tight">PRD §4 Open Questions & Chosen Defaults</h2>
            <p>
              The strategy specification leaves several execution and boundary conditions open. Below are the definitive design decisions and default rules implemented:
            </p>

            <div className="space-y-4">
              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Open Question #1: Universe Boundaries & Top 100 Exclusion</h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">LOCKED</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  <strong>Decision:</strong> Strategy strictly trades equities ranked <strong>101 to 750</strong> by market capitalization on the NSE (Nifty Midcap 150, Nifty Smallcap 250, Microcap 250). Large-cap stocks (ranks 1 to 100) are explicitly excluded from the equity trading universe.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Open Question #2: Overnight Gap-Down Stop-Loss Resolution</h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">LOCKED</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  <strong>Decision:</strong> If a stock gaps down overnight below the stop loss price (<code>Open &lt;= SL Price</code>), the stop exit fills at the <strong>Market Open price</strong> with slippage, NOT at the stop loss price. Realized trade loss exceeds 7% and portfolio drawdown exceeds 2%, avoiding unrealizable price improvement.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Open Question #3: Candidate Ranking Rule Under Capital Limits</h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">LOCKED</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  <strong>Decision:</strong> When multiple stocks generate entry signals on the same day under capital limits, candidates are prioritized by <strong>Momentum Breakout Score</strong>: <code>(Close - EMA20) / EMA20</code> descending. Candidates breaking furthest above their 20-day EMA are allocated capital first.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Open Question #4: Cash Equities Lot Sizing</h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">LOCKED</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  <strong>Decision:</strong> <code>lot_size</code> defaults to <strong>1 share</strong> for cash equities. Fractional share allocations are strictly floored to integers.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Open Question #5: Corporate Actions & Rolling 52-Week Ceiling</h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">LOCKED</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  <strong>Decision:</strong> All calculations operate on corporate action adjusted prices (<code>adj_close</code>). Historical high series is normalized by corporate adjustment factor, ensuring splits or bonuses do not distort breakout signals.
                </p>
              </div>

              <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Open Question #6: Friction & Slippage Cost Modeling</h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">LOCKED</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  <strong>Decision:</strong> Modeled at <strong>10 basis points (0.10%) per side</strong> (20 bps round-trip) applied directly to market executions.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 5. Parameter Guide & Runbook */}
        {activeTab === "runbook" && (
          <div className="space-y-6 text-slate-800 dark:text-slate-200 text-sm leading-relaxed">
            <h2 className="text-xl font-bold tracking-tight">How to Change a Strategy Parameter Walkthrough</h2>
            <p>
              Follow this 5-step process to add or modify a quantitative parameter across backend, OpenAPI contracts, and frontend dashboards:
            </p>

            <ol className="list-decimal pl-5 space-y-3 text-xs text-slate-600 dark:text-slate-300">
              <li>
                <strong>Update Backend Schema:</strong> Add the field to <code>StrategyConfig</code> in <code>backend/app/strategy/config.py</code> with appropriate validation bounds.
              </li>
              <li>
                <strong>Integrate in Engine:</strong> Consume the parameter in <code>signals.py</code> or <code>backtest.py</code> simulation loops.
              </li>
              <li>
                <strong>Regenerate OpenAPI:</strong> Run <code>make openapi</code> to export <code>frontend/openapi.json</code> and regenerate TypeScript definitions in <code>frontend/lib/schema.d.ts</code>.
              </li>
              <li>
                <strong>Expose in Frontend:</strong> Add corresponding form controls and state in <code>frontend/app/backtest/page.tsx</code> and <code>frontend/app/sweep/page.tsx</code>.
              </li>
              <li>
                <strong>Automated Validation:</strong> Run <code>make lint && make test</code> to enforce 100% test coverage and type-safety.
              </li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
