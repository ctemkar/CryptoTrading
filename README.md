# Crypto Master Consensus Engine v2.2

Automated cryptocurrency trading engine with SMA-based technical analysis, Gemini margin trading, and a real-time dashboard.

## Architecture

```
master_engine.py   – Core trading engine (runs every 15 min)
api.py             – Flask dashboard server (port 5001)
templates/         – Dashboard HTML
static/            – Static assets
```

## Features

- **SMA20/SMA50 Technical Analysis** on 15 crypto pairs
- **15 Coins**: BTC, ETH, SOL, XRP, LTC, DOGE, LINK, AVAX, DOT, ATOM, AAVE, UNI, FIL, SHIB, PEPE
- **Margin Shorts** on eligible pairs (BTC, ETH, SOL, XRP) — others are spot-only
- **Sentiment Classification** – Bullish / Bearish / Neutral with confidence %
- **Configurable Thresholds** via `.env` or at the top of `master_engine.py`
- **Automated Trading** via ccxt on Gemini
- **Supabase State Management** (optional) – positions, balance, trade history
- **Real-time Dashboard** at `localhost:5001`
- **Margin Pre-checks** to prevent insufficient funds errors
- **Position Flip Detection** – automatically closes opposing positions before opening new ones

## Setup

1. Clone and install:
   ```bash
   git clone https://github.com/ctemkar/CryptoTrading.git
   cd CryptoTrading
   pip install -r requirements.txt
   ```

2. Configure credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your Gemini API keys
   # Supabase is OPTIONAL — leave blank for local-only testing
   ```

3. Run:
   ```bash
   python api.py
   ```
   This starts both the engine (background) and dashboard at http://localhost:5001

## Running without Supabase

Supabase is **completely optional**. Without it:
- ✅ All trading and analysis works normally
- ✅ Dashboard shows live data
- ⚠️ Positions/trades are not persisted across restarts
- ⚠️ Equity chart won't have historical data

Just leave `SUPABASE_URL` and `SUPABASE_KEY` blank in your `.env`.

## Supabase Tables (optional)

| Table       | Purpose                          |
|-------------|----------------------------------|
| `equity`    | Balance snapshots over time      |
| `positions` | Open/closed positions            |
| `trades`    | Executed trade log               |

## Configuration

All settings are at the top of `master_engine.py` with documentation.
Key settings can also be overridden via environment variables in `.env`:

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Trade size | `TRADE_SIZE_USD` | $50 | Maximum USD per trade |
| Bearish threshold | `BEARISH_THRESHOLD` | 58% | Confidence needed for SHORT signal |
| Bullish threshold | `BULLISH_THRESHOLD` | 58% | Confidence needed for BUY signal |
| Cycle interval | `CYCLE_INTERVAL_MINUTES` | 15 min | Time between analysis cycles |
| Balance reserve | — | $20 | Minimum USD to keep in account |
| Trade size % | — | 15% | % of usable balance per trade |

### Threshold Guide

- **50-55%**: Very aggressive — trades on weak signals, more false positives
- **55-60%**: Aggressive — good for active trading in sideways markets
- **60-65%**: Moderate — balanced between activity and accuracy
- **65-75%**: Conservative — fewer but higher-conviction trades
- **75-90%**: Very conservative — only trades on strong trends

## License

Private – All rights reserved.
