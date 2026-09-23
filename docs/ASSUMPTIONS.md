# Project Assumptions & Methodology Rules

This document records the foundational assumptions, methodology decisions, and edge-case behaviors locked for the EquiTest NSE quantitative backtesting platform.

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
