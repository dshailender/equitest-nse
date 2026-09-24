# EquiTest NSE — Quantitative Strategy Specification

This document details the exact quantitative rules, mathematical formulas, and execution invariants governing the EquiTest NSE trading strategy (derived verbatim from PRD §2).

---

## 1. Trading Universe Selection
- **Eligible Universe**: Stocks listed on the National Stock Exchange of India (NSE) ranked **101 to 750 by market capitalization** (comprising Nifty Midcap 150, Nifty Smallcap 250, and Nifty Microcap 250).
- **Large-Cap Exclusion**: Stocks ranked 1 to 100 by market capitalization are strictly excluded from the equity trading universe.
- **Benchmark Series**: The NIFTY 50 index (`^NSEI` / `NIFTY50`) is ingested separately and used solely as an external macroeconomic regime filter; it is never traded as an equity asset.

---

## 2. Technical Indicators
All indicators are computed on corporate-action adjusted daily closing prices (`adj_close`):
1. **Exponential Moving Averages (EMAs)**:
   - Evaluated at spans of **20, 50, 150, and 200 days**:
     $$\text{EMA}_t = \alpha \cdot P_t + (1 - \alpha) \cdot \text{EMA}_{t-1}, \quad \alpha = \frac{2}{\text{span} + 1}$$
   - Warm-up periods require $\text{span}$ non-null sessions before valid output is produced.
2. **52-Week Rolling High**:
   - Rolling peak over a **252-day lookback window**, strictly shifted by 1 bar to prevent lookahead bias:
     $$\text{High52W}_t = \max \left( \text{High}_{t-252}, \dots, \text{High}_{t-1} \right)$$
   - Bar $t$'s own intraday high is never included in its 52-week reference ceiling.

---

## 3. Entry Signal Conditions
An entry signal triggers on session $T$ if and only if **all four conditions** are simultaneously satisfied:

1. **Market Regime Filter**:
   - Evaluated on the benchmark NIFTY 50 index:
     $$\text{NIFTY Close}_T > \text{EMA50}_T \quad \text{AND} \quad \text{NIFTY Close}_T > \text{EMA200}_T$$
   - *Invariant*: If this condition evaluates to `False`, **zero new entry signals** are generated across the entire universe on session $T$.
2. **Stock Trend Filter**:
   - Four EMAs strictly stacked in ascending order:
     $$\text{EMA20}_T > \text{EMA50}_T > \text{EMA150}_T > \text{EMA200}_T$$
3. **52-Week High Proximity Filter**:
   - Stock price is within 15% of its 52-week rolling peak:
     $$\text{Close}_T > 0.85 \times \text{High52W}_T$$
4. **EMA-20 Crossover Trigger**:
   - Closing price crosses from below to above the 20-day EMA:
     $$\text{Close}_T > \text{EMA20}_T \quad \text{AND} \quad \text{Close}_{T-1} < \text{EMA20}_{T-1}$$

---

## 4. Execution Timing & Transaction Frictions
- **Signal Date**: Session $T$ closing prices determine signal generation.
- **Execution Date**: Orders execute on the next trading session $T+1$ at the **Market Open price**.
- **Slippage & Costs**: Modeled at **10 basis points (0.10%) per side**:
  - Entry execution price: $\text{Open}_{T+1} \times 1.0010$
  - Exit execution price: $\text{Exit Price} \times 0.9990$

---

## 5. Risk Management & Position Sizing
1. **Stop Loss Level**:
   - Fixed at **7% below execution entry price**:
     $$\text{SL Price} = \text{Entry Price} \times (1 - 0.07) = \text{Entry Price} \times 0.93$$
2. **Portfolio Risk Allocation**:
   - Maximum risk of **2% of starting capital corpus** per position:
     $$\text{Risk Amount} = \text{Corpus} \times 0.02$$
3. **Share Quantity Sizing**:
   - Sized such that hitting the 7% stop loss loses exactly the 2% allocated risk:
     $$\text{Quantity} = \left\lfloor \frac{\text{Risk Amount}}{\text{Entry Price} - \text{SL Price}} \right\rfloor = \left\lfloor \frac{\text{Corpus} \times 0.02}{\text{Entry Price} \times 0.07} \right\rfloor$$
   - Discrete share quantities: rounded down to integer `floor(quantity)`.
4. **Capital Constraint & Concurrent Positions**:
   - Each position consumes $\sim 28.5\%$ of capital ($\frac{2\%}{7\%} \approx 28.57\%$).
   - The portfolio holds a maximum of **3 concurrent positions**. A 4th candidate on the same session is rejected if free cash is insufficient.

---

## 6. Exit Rules & Gap-Down Handling
Positions are liquidated at Market Open on session $T+1$ under any of the following conditions:

1. **Strategy Exit Trigger**:
   - Stock closing price drops below its 20-day EMA:
     $$\text{Close}_T < \text{EMA20}_T$$
   - Position liquidates at session $T+1$ Market Open.
2. **Intraday Stop-Loss Hit**:
   - If session $T$ intraday low falls below the stop-loss price ($\text{Low}_T \le \text{SL Price}$), exit triggers.
3. **Overnight Gap-Down Semantics**:
   - If session $T$ opens below the stop-loss price ($\text{Open}_T \le \text{SL Price}$), the trade executes at the **Market Open price**, absorbing the true market gap without artificial price improvement.

---

## 7. Candidate Prioritization (Ranking Rule)
When multiple stocks generate an entry signal on the same session under capital constraints:
- Candidates are prioritized by **Momentum Breakout Score**:
  $$\text{Score} = \frac{\text{Close}_T - \text{EMA20}_T}{\text{EMA20}_T} \quad \text{(descending)}$$
- Candidates whose closing prices have broken furthest above their 20-day EMA receive execution priority. Ties are broken alphabetically by ticker symbol.
