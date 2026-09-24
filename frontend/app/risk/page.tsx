"use client";

import React, { useCallback, useEffect, useState } from "react";
import { z } from "zod";
import {
  calculateRiskSize,
  fetchRiskConfig,
  type RiskConfigResponse,
  type RiskSizeResponse,
} from "../../lib/api";

const FormSchema = z.object({
  corpus: z.number({ invalid_type_error: "Corpus must be a number" }).positive("Corpus must be greater than 0"),
  entry: z.number({ invalid_type_error: "Entry price must be a number" }).positive("Entry price must be greater than 0"),
  sl_pct: z
    .number({ invalid_type_error: "Stop loss % must be a number" })
    .positive("Stop loss % must be greater than 0")
    .max(100, "Stop loss % must not exceed 100"),
  risk_pct: z
    .number({ invalid_type_error: "Risk % must be a number" })
    .positive("Risk % must be greater than 0")
    .max(100, "Risk % must not exceed 100"),
  lot_size: z
    .number({ invalid_type_error: "Lot size must be a number" })
    .int("Lot size must be an integer")
    .min(1, "Lot size must be at least 1"),
});

type FormValues = z.infer<typeof FormSchema>;

export default function RiskPage() {
  const [corpus, setCorpus] = useState<string>("500000");
  const [entry, setEntry] = useState<string>("100");
  const [slPct, setSlPct] = useState<string>("7");
  const [riskPct, setRiskPct] = useState<string>("2");
  const [lotSize, setLotSize] = useState<string>("1");

  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RiskSizeResponse | null>(null);
  const [config, setConfig] = useState<RiskConfigResponse | null>(null);

  // Load backend default config on mount
  useEffect(() => {
    async function loadConfig() {
      try {
        const defaultCfg = await fetchRiskConfig();
        setConfig(defaultCfg);
      } catch (err) {
        console.warn("Could not load backend risk config:", err);
      }
    }
    loadConfig();
  }, []);

  const computeSize = useCallback(async (
    c: number,
    e: number,
    sl: number,
    r: number,
    lot: number
  ) => {
    // Validate form inputs with Zod
    const validation = FormSchema.safeParse({
      corpus: c,
      entry: e,
      sl_pct: sl,
      risk_pct: r,
      lot_size: lot,
    });

    if (!validation.success) {
      const errors: Partial<Record<keyof FormValues, string>> = {};
      for (const issue of validation.error.issues) {
        const fieldName = issue.path[0] as keyof FormValues;
        if (!errors[fieldName]) {
          errors[fieldName] = issue.message;
        }
      }
      setFieldErrors(errors);
      setResult(null);
      return;
    }

    setFieldErrors({});
    setError(null);
    setLoading(true);

    try {
      const response = await calculateRiskSize({
        corpus: c,
        entry: e,
        sl_pct: sl / 100.0,
        risk_pct: r / 100.0,
        lot_size: lot,
      });
      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to calculate position size"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Compute initial position size on mount
  useEffect(() => {
    computeSize(500000, 100, 7, 2, 1);
  }, [computeSize]);

  const handleSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    const c = parseFloat(corpus);
    const e = parseFloat(entry);
    const sl = parseFloat(slPct);
    const r = parseFloat(riskPct);
    const lot = parseInt(lotSize, 10);
    computeSize(c, e, sl, r, lot);
  };

  const handleInputChange = (
    setter: React.Dispatch<React.SetStateAction<string>>,
    val: string,
    fieldName: keyof FormValues
  ) => {
    setter(val);
    const c = fieldName === "corpus" ? parseFloat(val) : parseFloat(corpus);
    const e = fieldName === "entry" ? parseFloat(val) : parseFloat(entry);
    const sl = fieldName === "sl_pct" ? parseFloat(val) : parseFloat(slPct);
    const r = fieldName === "risk_pct" ? parseFloat(val) : parseFloat(riskPct);
    const lot = fieldName === "lot_size" ? parseInt(val, 10) : parseInt(lotSize, 10);

    if (!isNaN(c) && !isNaN(e) && !isNaN(sl) && !isNaN(r) && !isNaN(lot)) {
      computeSize(c, e, sl, r, lot);
    }
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Risk & Position Sizing</h1>
        <p className="text-sm text-slate-500 mt-1">
          Derives exact share quantities and capital allocation from the 2% account risk rule and 7% hard stop loss (PRD §4).
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Form Card */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Risk Parameters</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="corpus" className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">
                Account Corpus (₹)
              </label>
              <input
                id="corpus"
                name="corpus"
                data-testid="input-corpus"
                type="number"
                step="any"
                value={corpus}
                onChange={(e) => handleInputChange(setCorpus, e.target.value, "corpus")}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="500000"
              />
              {fieldErrors.corpus && (
                <p className="text-xs text-red-600 mt-1" data-testid="error-corpus">{fieldErrors.corpus}</p>
              )}
            </div>

            <div>
              <label htmlFor="entry" className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">
                Proposed Entry Price (₹)
              </label>
              <input
                id="entry"
                name="entry"
                data-testid="input-entry"
                type="number"
                step="any"
                value={entry}
                onChange={(e) => handleInputChange(setEntry, e.target.value, "entry")}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="100"
              />
              {fieldErrors.entry && (
                <p className="text-xs text-red-600 mt-1" data-testid="error-entry">{fieldErrors.entry}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="sl_pct" className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">
                  Stop Loss (%)
                </label>
                <input
                  id="sl_pct"
                  name="sl_pct"
                  data-testid="input-sl"
                  type="number"
                  step="any"
                  value={slPct}
                  onChange={(e) => handleInputChange(setSlPct, e.target.value, "sl_pct")}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="7"
                />
                {fieldErrors.sl_pct && (
                  <p className="text-xs text-red-600 mt-1" data-testid="error-sl">{fieldErrors.sl_pct}</p>
                )}
              </div>

              <div>
                <label htmlFor="risk_pct" className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">
                  Max Risk / Trade (%)
                </label>
                <input
                  id="risk_pct"
                  name="risk_pct"
                  data-testid="input-risk"
                  type="number"
                  step="any"
                  value={riskPct}
                  onChange={(e) => handleInputChange(setRiskPct, e.target.value, "risk_pct")}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="2"
                />
                {fieldErrors.risk_pct && (
                  <p className="text-xs text-red-600 mt-1" data-testid="error-risk">{fieldErrors.risk_pct}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="lot_size" className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-1">
                Share Lot Multiple
              </label>
              <input
                id="lot_size"
                name="lot_size"
                data-testid="input-lot"
                type="number"
                step="1"
                value={lotSize}
                onChange={(e) => handleInputChange(setLotSize, e.target.value, "lot_size")}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="1"
              />
              {fieldErrors.lot_size && (
                <p className="text-xs text-red-600 mt-1" data-testid="error-lot">{fieldErrors.lot_size}</p>
              )}
            </div>

            <button
              id="calculate-btn"
              data-testid="btn-calculate"
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm shadow-sm transition-colors disabled:opacity-50"
            >
              {loading ? "Calculating..." : "Calculate Position Size"}
            </button>
          </form>
        </div>

        {/* Results Card */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Position Sizing Output</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                <span className="text-xs text-slate-500 font-medium block">Position Size (Quantity)</span>
                <span
                  data-testid="result-qty"
                  className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1 block"
                >
                  {result ? result.qty.toLocaleString("en-IN") : "—"}
                </span>
                <span className="text-xs text-slate-400 mt-0.5 block">Shares (Integer floored)</span>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                <span className="text-xs text-slate-500 font-medium block">Capital Required</span>
                <span
                  data-testid="result-capital"
                  className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1 block"
                >
                  {result ? formatINR(result.capital_required) : "—"}
                </span>
                <span className="text-xs text-slate-400 mt-0.5 block">
                  {result && parseFloat(corpus) > 0
                    ? `${((result.capital_required / parseFloat(corpus)) * 100).toFixed(2)}% of account corpus`
                    : "—"}
                </span>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                <span className="text-xs text-slate-500 font-medium block">Stop Loss Price Level</span>
                <span
                  data-testid="result-sl-price"
                  className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1 block"
                >
                  {result ? formatINR(result.sl_price) : "—"}
                </span>
                <span className="text-xs text-slate-400 mt-0.5 block">
                  {slPct}% below entry price
                </span>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                <span className="text-xs text-slate-500 font-medium block">Corpus Risk Amount</span>
                <span
                  data-testid="result-risk-amount"
                  className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1 block"
                >
                  {result ? formatINR(result.risk_amount) : "—"}
                </span>
                <span className="text-xs text-slate-400 mt-0.5 block">
                  {riskPct}% max account risk limit
                </span>
              </div>
            </div>
          </div>

          {/* PRD Sizing Invariants & Rules */}
          <div className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-6 text-sm text-slate-600 dark:text-slate-400 space-y-3">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">Formula & Allocation Rules (PRD §4)</h3>
            <ul className="list-disc pl-5 space-y-1.5 text-xs">
              <li>
                <strong>Quantity Derivation:</strong> <code>floor( (Corpus × Risk%) / (Entry × SL%) / LotSize ) × LotSize</code>.
              </li>
              <li>
                <strong>Capital Exposure:</strong> Risking 2% at a 7% stop loss requires allocating <strong>~28.5%</strong> of capital per trade.
              </li>
              <li>
                <strong>Concurrent Trades:</strong> The framework supports a maximum of <strong>3 to 4 concurrent positions</strong> under a 100% total exposure limit.
              </li>
              <li>
                <strong>Slippage & Frictions:</strong> Realized trades incur <strong>{config ? config.cost_bps : 10} bps</strong> (0.10%) per side for brokerage, STT, and slippage.
              </li>
              <li>
                <strong>Overnight Gap-Down:</strong> If the session opens below the stop loss price, the trade exits at the Open price, realistically absorbing losses &gt; 7%.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

