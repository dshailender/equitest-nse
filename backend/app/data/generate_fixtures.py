from pathlib import Path

import numpy as np
import pandas as pd

from app.data.ingest import validate_ohlcv_dataframe


def generate_ohlcv_series(
    start_date: str = "2019-01-01",
    end_date: str = "2024-01-01",
    initial_price: float = 1000.0,
    volatility: float = 0.015,
    split_date: str | None = None,
    split_ratio: float = 2.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Generates synthetic daily OHLCV series adhering to all financial invariants."""
    # Generate business days
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    n = len(dates)
    np.random.seed(seed)

    # Random walk for close prices
    returns = np.random.normal(loc=0.0004, scale=volatility, size=n)
    price_factors = np.cumprod(1 + returns)
    raw_close = initial_price * price_factors

    # Apply corporate action (e.g. split) if specified
    unadj_close = raw_close.copy()
    adj_close = raw_close.copy()

    if split_date:
        split_dt = pd.to_datetime(split_date)
        mask_after = dates >= split_dt
        mask_before = dates < split_dt
        # Unadjusted close drops by split_ratio after split
        unadj_close[mask_after] = unadj_close[mask_after] / split_ratio
        # Adjusted close normalized to post-split level
        adj_close[mask_before] = adj_close[mask_before] / split_ratio
        adj_close[mask_after] = unadj_close[mask_after]

    # Derive Open, High, Low, and Volume
    open_pct = np.random.uniform(-0.005, 0.005, size=n)
    opens = unadj_close * (1 + open_pct)

    high_pct = np.random.uniform(0.002, 0.015, size=n)
    low_pct = np.random.uniform(0.002, 0.015, size=n)

    highs = np.maximum(opens, unadj_close) * (1 + high_pct)
    lows = np.minimum(opens, unadj_close) * (1 - low_pct)
    volumes = np.random.randint(100_000, 5_000_000, size=n).astype(float)

    df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "open": np.round(opens, 2),
            "high": np.round(highs, 2),
            "low": np.round(lows, 2),
            "close": np.round(unadj_close, 2),
            "adj_close": np.round(adj_close, 2),
            "volume": volumes,
        }
    )
    return df


def generate_constituents() -> pd.DataFrame:
    """Generates constituent lists for 3 historical dates (ranks 1 to 750)."""
    dates = ["2020-01-01", "2022-01-01", "2024-01-01"]
    records = []

    for d in dates:
        # In 2020: base order
        # In 2022: rotated slightly
        # In 2024: rotated further
        shift = 0 if d == "2020-01-01" else (10 if d == "2022-01-01" else 25)
        for rank in range(1, 751):
            if rank <= 100:
                sym = f"TOP_{rank}"
            else:
                sym_num = ((rank + shift - 101) % 650) + 101
                sym = f"MIDCAP_STOCK_{sym_num}"
            records.append({"date": d, "symbol": sym, "rank": rank})

    return pd.DataFrame(records)


def main():
    fixtures_dir = (
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "fixtures"
    )
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # 1. NIFTY 50 Benchmark Index
    nifty_df = generate_ohlcv_series(
        start_date="2019-01-01",
        end_date="2024-01-01",
        initial_price=11000.0,
        volatility=0.010,
        seed=42,
    )
    validate_ohlcv_dataframe(nifty_df)
    nifty_df.to_parquet(fixtures_dir / "NIFTY50.parquet", index=False)
    nifty_df.to_parquet(fixtures_dir / "^NSEI.parquet", index=False)

    # 2. Key Equities (with RELIANCE including a corporate action split on 2021-06-01)
    reliance_df = generate_ohlcv_series(
        start_date="2019-01-01",
        end_date="2024-01-01",
        initial_price=1500.0,
        volatility=0.018,
        split_date="2021-06-01",
        split_ratio=2.0,
        seed=42,
    )
    validate_ohlcv_dataframe(reliance_df)
    reliance_df.to_parquet(fixtures_dir / "RELIANCE.parquet", index=False)

    for sym, price, vol in [
        ("HDFCBANK", 1200.0, 0.014),
        ("INFY", 800.0, 0.016),
        ("TATAMOTORS", 300.0, 0.025),
    ]:
        df = generate_ohlcv_series(
            start_date="2019-01-01",
            end_date="2024-01-01",
            initial_price=price,
            volatility=vol,
            seed=42,
        )
        validate_ohlcv_dataframe(df)
        df.to_parquet(fixtures_dir / f"{sym}.parquet", index=False)

    # Midcap Constituents (Ranks 101 to 150)
    for i in range(101, 151):
        sym = f"MIDCAP_STOCK_{i}"
        if i == 101:
            price = 450.0
            vol = 0.022
            seed = 42
        elif i == 143:
            price = 150.0 + float((i * 37) % 1200)
            vol = 0.016 + float((i * 7) % 15) * 0.001
            seed = 186
        else:
            price = 150.0 + float((i * 37) % 1200)
            vol = 0.016 + float((i * 7) % 15) * 0.001
            seed = 42 + i

        df = generate_ohlcv_series(
            start_date="2019-01-01",
            end_date="2024-01-01",
            initial_price=price,
            volatility=vol,
            seed=seed,
        )
        validate_ohlcv_dataframe(df)
        df.to_parquet(fixtures_dir / f"{sym}.parquet", index=False)

    # 3. Constituents point-in-time
    const_df = generate_constituents()
    const_df.to_parquet(fixtures_dir / "constituents.parquet", index=False)
    print(f"Generated test parquet fixtures in {fixtures_dir}")


if __name__ == "__main__":
    main()
