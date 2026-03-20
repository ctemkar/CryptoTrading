# Crypto Master Consensus Engine v2.1

Automated cryptocurrency trading engine with SMA-based technical analysis, Gemini margin trading, and a real-time dashboard.

## Architecture

```
master_engine.py   – Core trading engine (runs every 15 min)
api.py             – Flask dashboard server (port 5001)
templates/         – Dashboard HTML
static/            – Static assets
```

## Features

- **SMA20/SMA50 Technical Analysis** on 6 crypto pairs (BTC, ETH, SOL, LTC, XRP, DOGE)
- **Sentiment Classification** – Bullish / Bearish / Neutral with confidence %
- **Automated Trading** via ccxt on Gemini Margin
- **Supabase State Management** – positions, balance, trade history (single source of truth)
- **Real-time Dashboard** at `localhost:5001`
- **Margin Pre-checks** to prevent insufficient funds errors
- **Position Flip Detection** – automatically closes opposing positions before opening new ones

## Setup

1. Clone and install:
   ```bash
   git clone https://github.com/ctemkar/crypto-master-engine.git
   cd crypto-master-engine
   pip install -r requirements.txt
   ```

2. Configure credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your Gemini and Supabase keys
   ```

3. Run:
   ```bash
   python api.py
   ```
   This starts both the engine (background) and dashboard at http://localhost:5001

## Supabase Tables

| Table       | Purpose                          |
|-------------|----------------------------------|
| `equity`    | Balance snapshots over time      |
| `positions` | Open/closed positions            |
| `trades`    | Executed trade log               |

## Configuration

Key settings in `master_engine.py`:
- `TRADE_SIZE_USD` – USD per trade (default: $50)
- `MIN_BALANCE_RESERVE` – Minimum balance to keep (default: $20)
- `CYCLE_INTERVAL_MINUTES` – Analysis frequency (default: 15 min)
- `BEARISH_THRESHOLD` / `BULLISH_THRESHOLD` – Confidence thresholds (default: 65%)

## License

Private – All rights reserved.
