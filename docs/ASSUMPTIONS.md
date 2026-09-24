# Project Assumptions & Methodology Rules

This document records the foundational assumptions, methodology decisions, and edge-case behaviors locked for the EquiTest NSE quantitative backtesting platform.

---

## 0. PRD §4 Open Questions & Design Decisions (Consolidated)

The PRD defines several open questions regarding strategy execution, edge cases, and portfolio constraints. Below are the locked implementation choices and defaults:

### Open Question #1: Universe Selection & Large-Cap Exclusion
- **PRD Query**: Should the strategy include large-cap stocks (Nifty 50, Nifty Next 50) or focus strictly on mid/small-caps?
- **Locked Choice**: The strategy strictly trades equities ranked **101 to 750 by market capitalization** (Nifty Midcap 150, Nifty Smallcap 250, Microcap 250). Large-caps (ranks 1 to 100) are explicitly excluded from the equity trading universe.
- **Rationale**: The 4-EMA trend following and 52-week breakout momentum strategy targets high-beta growth stocks rather than mature large-caps.
- `TODO: PO confirm` whether parameter sweeps across custom rank bands (e.g. 101–250 for Midcap only) should become strategy profiles in the UI.

### Open Question #2: Stop Loss Execution on Overnight Gap-Downs
- **PRD Query**: If a stock gaps down overnight below the 7% stop loss price ($\text{Open}_T \le \text{SL Price}$), at what price does the exit order fill?
- **Locked Choice**: The stop exit fills at the **Market Open price** ($\text{Exit Price} = \text{Open}_T \times 0.9990$), NOT at the stop loss price.
- **Rationale**: Modeling fills at the stop-loss price would represent unrealizable price improvement during market gap events. Realized losses exceed 7% ($\text{Loss} > 7\%$) and portfolio drawdown exceeds 2%, accurately capturing market gap risk.

### Open Question #3: Candidate Ranking Rule Under Capital Constraints
- **PRD Query**: When multiple universe constituents trigger entry signals simultaneously and free portfolio capital cannot fund all candidates, what is the prioritization rule?
- **Locked Choice**: Candidates are ranked by **Momentum Breakout Score** descending:
  $$\text{Score} = \frac{\text{Close}_T - \text{EMA20}_T}{\text{EMA20}_T} \quad \text{(descending)}$$
- **Rationale**: Prioritizes stocks whose closing prices have broken furthest above their 20-day exponential moving average, maximizing initial momentum. Ties are broken alphabetically by ticker symbol. Pluggable rankers (`alphabetical`, `52w_proximity`) are supported via `ranking_method`.
- `TODO: PO confirm` whether secondary tie-breaking should incorporate relative volume breakout metrics.

### Open Question #4: Cash Equities Lot Sizing
- **PRD Query**: Should the engine enforce discrete share quantities or fractional shares, and should lot sizes default to 1?
- **Locked Choice**: `lot_size` defaults to **1 share** for NSE cash equities. Fractional shares are prohibited; quantities are floored to integer shares via `floor(Risk Amount / (Entry * 0.07))`.
- `TODO: PO confirm` whether lot sizing configuration should support derivatives basket multiples if F&O contracts are traded in future phases.

### Open Question #5: Corporate Actions & Rolling 52-Week Ceiling
- **PRD Query**: How should splits, bonus issues, and dividends affect rolling 52-week highs and moving averages?
- **Locked Choice**: All calculations operate on **corporate action adjusted prices** (`adj_close`). The rolling 52W high is normalized by the historical corporate action adjustment ratio (`high * (adj_close / close)`), ensuring splits do not distort historical price ceilings.

### Open Question #6: Friction & Slippage Cost Modeling
- **PRD Query**: What transaction costs and slippages should be assumed for mid/small-cap NSE equities?
- **Locked Choice**: A fixed **10 basis points (0.10%) per side** ($0.20\%$ round trip) is applied to all market orders ($\text{Buy} = \text{Price} \times 1.0010$, $\text{Sell} = \text{Price} \times 0.9990$).
- `TODO: PO confirm` whether exchange turnover charges, STT (Securities Transaction Tax), GST, and stamp duty should be itemized separately from execution slippage.

---

## 1. Trading Universe & Bias Prevention


1. **Trading Universe Constituents (NSE 101–750)**:
   - **Exclusion of Top 100**: The strategy strictly trades stocks ranked 101 to 750 by market capitalization (Nifty Midcap 150, Nifty Smallcap 250, and Microcap 250). Large-cap stocks (ranks 1 to 100) are explicitly excluded from the equity trading universe.
   - **Benchmark Index**: NIFTY 50 (`^NSEI` / `NIFTY50`) benchmark is ingested and tracked separately solely for the market regime filter (`NIFTY > EMA 50` and `NIFTY > EMA 200`) and does not enter the stock trading universe.
   - **Survivorship Bias Handling**: Point-in-time constituent lists are resolved via `/data/fixtures/constituents.parquet` or `universe_membership` database records. If point-in-time data is missing for historical dates, the current constituent list is used as fallback, and `survivorship_bias: true` is explicitly flagged.

---

## 2. Technical Indicators & Mathematical Formulas

1. **Exponential Moving Averages (EMAs)**:
   - **Formula**: Vectorized calculation using pandas `.ewm(span=span, adjust=False, min_periods=span).mean()` with smoothing factor $\alpha = \frac{2}{span + 1}$.
   - **Price Input**: All equity EMAs are computed on corporate-action adjusted close (`adj_close`).
   - **Warm-up Window**: Initial $(span - 1)$ sessions produce `NaN` (or `null` in JSON responses). The first valid non-NaN value begins exactly at row $span$ (e.g., EMA-200 begins at row 200).
   - **Accuracy**: Verified to match standard technical analysis libraries (TA-Lib) within numerical tolerance of $10^{-6}$.

2. **52-Week Rolling High**:
   - **Lookback Window**: 252 trading sessions (approx. 52 trading weeks in Indian equity markets).
   - **No Look-Ahead Guarantee**: Implemented as `high.shift(1).rolling(window=252, min_periods=252).max()`. Bar $N$'s 52W high equals $\max(high[N-252:N])$ and strictly excludes bar $N$'s own high.
   - **Corporate Action Continuity**: If a stock underwent splits or bonus issues, the high series is normalized by the corporate adjustment factor (`high * (adj_close / close)`) to prevent distorted historical highs from invalidating breakout signals.

---

## 3. Order Execution & Look-Ahead Prevention

1. **Signal Generation & Order Execution**:
   - Indicator values and trading signals are evaluated on session $T$ closing prices.
   - Any trade triggered on session $T$ executes on session $T+1$ at the **Market Open price**.
   - No intraday look-ahead is permitted in end-of-day backtesting.

2. **Price Filters**:
   - The 52W high filter requires `Price > 0.85 × 52W High` (i.e. within 15% of the 52-week high).

---

## 4. Signal Rules & Filter Invariants (Phase 3)

1. **Market Regime Filter (REQ-3.1)**:
   - **Condition**: Evaluated on NIFTY 50 closing price: `NIFTY Close > EMA 50 AND NIFTY Close > EMA 200`.
   - **Zero Trade Invariant**: If market regime evaluates to False on session $T$, all entry signals across the entire universe are rejected (`entry_signal = False`).
   - **Lookback Warm-up**: Before bar 200 of the benchmark series, regime evaluates to `False`.

2. **Stock Trend Filter (REQ-3.2)**:
   - **Condition**: Evaluated on equity adjusted close: `EMA 20 > EMA 50 > EMA 150 > EMA 200`.
   - **Strict Hierarchy**: All four EMAs must be strictly stacked. If any adjacent EMAs are equal or inverted, trend evaluates to `False`.

3. **52-Week High Proximity Filter (REQ-3.3)**:
   - **Condition**: `Close > 0.85 × 52W High` (strictly within 15% of the rolling 252-day peak).
   - **Scale Consistency**: Both the price and 52W high series use corporate-action adjusted pricing.

4. **Entry Trigger & Crossover Invariant (REQ-3.4)**:
   - **Formula**: `(Regime & Trend & Near52W) on T AND (Close_T > EMA20_T) AND (Close_{T-1} < EMA20_{T-1})`.
   - **Strict Crossover**: By default, bar $T-1$ requires `Close < EMA20`.
   - `TODO: PO confirm` whether exact equality at bar $T-1$ (`Close(T-1) == EMA20(T-1)`) should trigger an entry signal. Parameterized via `StrategyConfig.allow_crossover_equal = False`.

5. **Exit Trigger Invariant (REQ-3.5)**:
   - **Formula**: `Close(T) < EMA20(T)`.
   - **Execution**: Signal generated on bar $T$ close; execution occurs on session $T+1$ at Market Open.

---

## 5. Risk Management, Sizing & Stop Loss Invariants (Phase 4)

1. **Initial Stop Loss Calculation (REQ-4.1)**:
   - **Formula**: `SL Price = Entry Price × (1 - 0.07)` (7% hard stop loss).
   - **Execution**: Evaluated on subsequent trading sessions. If $\text{Low}_T \le \text{SL Price}$, a stop loss exit is triggered.

2. **Dynamic Account Risk (REQ-4.2)**:
   - **Formula**: `Risk Amount = Current Corpus × 0.02` (2% risk per trade).
   - **Dynamic Adjustment**: Initial risk on ₹5,00,000 starting corpus is ₹10,000. Compounding increases dollar risk during equity peaks and reduces dollar risk during portfolio drawdowns.

3. **Position Sizing Derivation (REQ-4.3)**:
   - **Formula**:
     $$\text{Raw Qty} = \frac{\text{Corpus} \times \text{Risk \%}}{\text{Entry Price} \times \text{SL \%}}$$
     $$\text{Quantity} = \left\lfloor \frac{\text{Raw Qty}}{\text{Lot Size}} \right\rfloor \times \text{Lot Size}$$
   - **PRD Invariant & Arithmetic Relationship**:
     - At ₹5,00,000 corpus and ₹100 entry: Risk is ₹10,000, SL distance is ₹7.00 $\implies \text{Qty} = \lfloor 10000 / 7 \rfloor = 1,428$ shares, requiring ₹1,42,800 capital ($\approx 28.56\%$ allocation).
     - At ₹1,00,000 corpus and ₹100 entry: Risk is ₹2,000, SL distance is ₹7.00 $\implies \text{Qty} = \lfloor 2000 / 7 \rfloor = 285$ shares, requiring ₹28,500 capital ($28.5\%$ allocation).
     - `TODO: PO confirm` whether lot sizes for cash equities default strictly to 1 or should support index derivative/basket lot sizes. Currently defaulted to `lot_size = 1`.

4. **Overnight Gap-Down Semantics (Explicit Assumption)**:
   - If a stock opens below the stop loss price ($\text{Open}_T \le \text{SL Price}$), the stop exit executes at the **Open price** rather than the stop loss price.
   - *Impact*: Realized trade loss exceeds 7% ($\text{Loss} > 7\%$) and portfolio loss exceeds 2% ($\text{Drawdown} > 2\%$). The backtesting engine records realistic market gaps without artificial price improvement.

5. **Transaction Frictions & Slippage (REQ-0.3)**:
   - Modeled at **10 basis points (0.10%) per side**:
     - Buy execution: $\text{Price} \times 1.0010$
     - Sell execution: $\text{Price} \times 0.9990$

6. **Portfolio Exposure & Capital Allocation**:
   - System enforces total portfolio exposure $\le \text{Corpus}$.
   - Because each trade requires $\sim 28.5\%$ of capital, the portfolio naturally caps at a maximum of **3 to 4 concurrent positions**. New entry signals are rejected if $\text{Open Positions Value} + \text{Required Capital} > \text{Corpus}$.

---

## 6. Backtest Simulation Engine & Capital Constraints (Phase 5)

1. **Signal Clashing & Ranking Rule (PRD Open Question #3 / REQ-5.3)**:
   - When multiple universe stocks generate an entry signal on the same session $T-1$, candidates are ranked by momentum score:
     $$\text{Score} = \frac{\text{Close}_{T-1} - \text{EMA20}_{T-1}}{\text{EMA20}_{T-1}} \quad \text{(descending)}$$
   - `DefaultRanker` prioritizes stocks whose closing prices have broken furthest above their 20-day EMA. Pluggable `Ranker` protocol allows custom ranking functions.
   - `TODO: PO confirm` whether tie-breakers should incorporate volume breakout ratio or liquidity filters beyond symbol alphabetical sorting.

2. **Capital Constraint & Position Rejections (REQ-5.3)**:
   - Total exposure constraint enforces `sum(open positions value) + required capital <= corpus`.
   - On ₹5,00,000 starting corpus with ~28.5% position allocation, a maximum of 3 concurrent positions can be opened. The 4th concurrent signal on the same session is rejected with `reason: "insufficient_capital"` and logged in `BacktestResult.rejections`.

3. **Execution Semantics & Ordering**:
   - On each session $T$:
     1. Exits are evaluated and executed first at Market Open (SL hit, gap-down, or $T-1$ exit signal).
     2. Free capital is updated.
     3. Entry candidates from $T-1$ signals are ranked and executed at Market Open with buy slippage until free capital is exhausted.
     4. Portfolio equity is marked-to-market using session $T$ closing prices.

---

## 7. Parameter Sweeps, Scenario Testing & Versioning (Phase 6)

1. **Config Schema & Backward Compatibility (REQ-6.1)**:
   - `StrategyConfig` is implemented as a Pydantic v2 `BaseModel` supporting runtime validation (`gt=0`, `lt=1`, etc.), dictionary serialization (`to_dict()`), and legacy alias compatibility (`corpus` $\leftrightarrow$ `capital`, `stop_loss_pct` $\leftrightarrow$ `sl_pct`, `ema_trend_spans` $\leftrightarrow$ `ema_spans`, `regime_spans` $\leftrightarrow$ `regime_ema_spans`).
   - Percentage parameters (`sl_pct`, `risk_pct`) automatically normalize whole numbers $\ge 1.0$ (e.g. $5 \to 0.05$, $2 \to 0.02$) to fractional decimals for seamless user input.

2. **Pluggable Ranking Protocols**:
   - Supported candidate prioritization rules:
     - `"momentum"`: Sort by breakout percentage above EMA-20: $(Close_{T-1} - EMA20) / EMA20$ descending.
     - `"alphabetical"`: Deterministic lexical sort by ticker symbol ascending.
     - `"52w_proximity"`: Proximity to 52-week rolling peak: $Close_{T-1} / High52W_{T-1}$ descending.

3. **Universe Rank Parameterization**:
   - `universe_start_rank` (default 101) and `universe_end_rank` (default 750) allow parameter sweeps across market-cap segments (e.g., Midcap 150: 101–250, Smallcap 250: 251–500, Microcap 250: 501–750).

4. **Cartesian Sweep Limits & Execution Semantics (REQ-6.2)**:
   - Parameter sweeps generate the full Cartesian product across candidate parameter lists.
   - Grid size is capped at 50 permutations per request to prevent worker saturation.
   - Sweep runs execute asynchronously in background tasks, reporting live status (`pending`, `running`, `partial`, `completed`, `failed`) and per-child progress metrics.

5. **Multi-Run Metric Alignment & Overlaid Curves (REQ-6.3)**:
   - Comparison endpoint (`GET /api/v1/backtest/compare?run_ids=...`) returns aligned performance metrics and synchronized mark-to-market equity curves across multiple runs for side-by-side evaluation.

6. **Annualized Returns & Config Versioning**:
   - All completed runs record `config_version="1.0"`, optional parent `sweep_id`, `cagr` computed as $\left(\frac{\text{Final Capital}}{\text{Initial Capital}}\right)^{\frac{252}{N}} - 1$, and `max_drawdown_pct`.

---

## 8. Reporting, Performance Metrics & Exports (Phase 7)

1. **Performance Metric Mathematical Specifications (REQ-7.1)**:
   - **Annualization Factor**: 252 trading sessions per calendar year for Indian markets.
   - **CAGR**: $\left(\frac{\text{Final Capital}}{\text{Initial Capital}}\right)^{\frac{252}{N}} - 1$, where $N$ is total trading sessions in the equity curve.
   - **Max Drawdown**: Peak-to-trough decline on daily marked-to-market equity. Both percentage (`max_drawdown_pct`, 4 decimal places) and absolute rupee loss (`max_drawdown_amount`, 2 decimal places) are calculated.
   - **Sharpe Ratio**: Risk-free rate $r_f = 0.0$. Annualized as $\frac{\mu_r}{\sigma_r} \times \sqrt{252}$, matching `empyrical.sharpe_ratio(..., risk_free=0, period="daily")` to within $10^{-6}$.
   - **Sortino Ratio**: Minimum Acceptable Return $\text{MAR} = 0.0$, annualization 252. Downside deviation is computed over all return observations with positive returns clipped to 0: $\sigma_d = \sqrt{\frac{1}{N}\sum \min(0, r_i)^2}$, matching `empyrical.sortino_ratio(..., required_return=0, period="daily")` to within $10^{-6}$.
   - **Calmar Ratio**: $\frac{\text{CAGR}}{|\text{Max Drawdown \%}|}$. If drawdown is zero or CAGR is negative, Calmar is set to 0.0.
   - **Profit Factor**: $\frac{\sum \text{Gross Profits}}{\sum |\text{Gross Losses}|}$. If gross losses are zero, returns $\infty$ (`float('inf')`, formatted as `"∞"` in UI and `"Infinity"` in JSON).
   - **Expectancy**: Monetary average return per closed trade: $(\text{Win Rate} \times \text{Avg Profit}) - ((1 - \text{Win Rate}) \times |\text{Avg Loss}|)$ in INR.
   - **Avg Days Held**: Arithmetic mean of duration in calendar days from entry to exit across all closed trades (1 decimal place).
   - **Decimal Serialization**: All float metrics support conversion to Python `Decimal` via `to_decimal_dict()` with precision matching documented requirements (2 decimal places for INR, 4 for rates/ratios, 1 for days).

2. **Monthly Returns Aggregation Matrix (REQ-7.2)**:
   - Aggregated directly from daily marked-to-market portfolio equity curves.
   - Monthly return is compounded as $\frac{\text{Equity}_{\text{month\_end}}}{\text{Equity}_{\text{month\_start}}} - 1.0$.
   - Missing months prior to the backtest start or after the backtest end are represented as `null`, avoiding artificial zero-return distortion.
   - Annual return is compounded across available trading months: $\prod (1 + r_m) - 1.0$.

3. **Multi-Format Export Engine (REQ-7.3)**:
   - **CSV Export**: Trade ledger table (`{run_id}_trades.csv`).
   - **XLSX Export**: Multi-worksheet OpenXML workbook (`Executive Summary`, `Performance Metrics`, `Trade Ledger`, `Monthly Returns`). Implemented using standard library `zipfile` and SpreadsheetML XML, requiring zero third-party C-extensions or external dependencies.
   - **ZIP Export**: Complete archive containing `metrics.csv`, `trades.csv`, `monthly_returns.csv`, and `equity_curve.csv`.
