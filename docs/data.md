# Market Data Pipeline & Corporate Action Adjustments

## 1. Overview
The EquiTest NSE framework provides market data ingestion and universe selection for Indian equities (NSE 101–750) and benchmark indices (`^NSEI` / NIFTY 50). All price series adhere to strict financial invariants, temporal monotonic ordering, and corporate-action adjustments.

---

## 2. Corporate Actions & Adjusted Close (`adj_close`)

### Why Unadjusted Prices Break Technical Strategies
In trend-following strategies utilizing Moving Averages (e.g. 20, 50, 150, 200 EMAs):
1. **Stock Splits & Bonus Issues**: If a stock with price ₹2,000 executes a 2:1 split or 1:1 bonus issue, its traded price drops overnight to ₹1,000 without any change in company enterprise value or investor economic worth.
2. **False Crossover Signals**: An unadjusted price drop of 50% causes the price to crash below the 20-day, 50-day, and 200-day EMAs, triggering false stop-losses, erroneous exit signals, and breaking EMA stack filters (`EMA 20 > EMA 50 > EMA 150 > EMA 200`).
3. **Historical Indicator Distortions**: Unadjusted prices distort historical high/low calculations (such as the 52-week high filter: `Price > 0.85 × 52W High`).

### The Adjustment Methodology
The framework populates the `adj_close` column for every session:
- **Cumulative Adjustment Factor**: Multiplies past prices by historical split, bonus, and rights ratios so the historical series remains economically continuous.
- **Dividends**: Large special dividends are adjusted to reflect true economic return.
- **Indicator Ground Truth**: All strategy indicators (EMAs, 52W High, Crossovers) in Phase 2+ must be computed on `adj_close` or adjusted OHLC.

---

## 3. Data Integrity & Validation Invariants

Every ingested OHLCV dataframe undergoes strict validation prior to database persistence (`app.data.ingest.validate_ohlcv_dataframe`):

| Invariant | Validation Rule | Rationale |
| :--- | :--- | :--- |
| **Monotonic Dates** | $Date_{t} > Date_{t-1}$ strictly increasing | Prevents time-travel leaks, duplicate sessions, and sorting anomalies. |
| **No Missing Values** | No `NaN` or `None` in Open, High, Low, Close, Adj Close | Eliminates imputation biases in backtest calculations. |
| **Session Bounds** | $High \ge Low$, $High \ge Open$, $High \ge Close$ | Verifies bar physical limits and data vendor feed integrity. |
| **Floor Bounds** | $Low \le Open$ and $Low \le Close$ | Asserts low is the minimum trading price of the session. |
| **Positive Prices** | $Price > 0$ for all OHLC and Adj Close | Equity prices cannot be negative or zero. |
| **Volume Non-Negative** | $Volume \ge 0$ | Trading volume is positive or zero for low-liquidity days. |

---

## 4. Survivorship Bias & Point-in-Time Universe

### The Survivorship Hazard
If a backtest runs from 2010 to 2025 using the *current* 2025 list of NSE 101–750 stocks:
- Companies that went bankrupt, merged, or fell out of the index between 2010 and 2024 are omitted.
- Only the "survivors" and top compounders are included, producing unrealistically inflated backtest performance.

### Point-in-Time Tracking
- **Point-in-Time Resolution**: `app/data/universe.py` checks `universe_membership` and `/data/fixtures/constituents.parquet` for exact historical constituent rankings on that date.
- **Survivorship Bias Flag**: If historical constituent lists are available, `survivorship_bias = False`. If only the fallback current universe can be used, `survivorship_bias = True` is explicitly returned and rendered in UI diagnostics.

---

## 5. Look-Ahead Leak Prevention
- Ingestion queries require explicit start and end filters.
- `GET /api/v1/prices/{symbol}?end=D` strictly limits returned sessions to $Date \le D$.
- Signals generated on session $T$ execute only on session $T+1$ open.

