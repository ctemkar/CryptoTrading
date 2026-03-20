#!/usr/bin/env python3
"""
Crypto Master Consensus Engine v2.1
====================================
Automated cryptocurrency trading engine that:
- Performs SMA20/SMA50 technical analysis on crypto pairs
- Generates sentiment signals (BULLISH/BEARISH/NEUTRAL)
- Executes trades via ccxt on Gemini exchange
- Uses Supabase as the single source of truth for state management
- Runs every 15 minutes via scheduler

Supported pairs: BTCUSD, ETHUSD, SOLUSD, LTCUSD, XRPUSD, DOGEUSD
"""

import os
import sys
import time
import json
import logging
import traceback
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

import ccxt
import schedule
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_SECRET = os.getenv("GEMINI_API_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "LTC/USD", "XRP/USD", "DOGE/USD"]
SYMBOL_MAP = {s: s.replace("/", "") for s in SYMBOLS}  # BTC/USD -> BTCUSD

SMA_SHORT = 20
SMA_LONG = 50
CANDLE_TIMEFRAME = "1h"
CANDLE_LIMIT = 60  # enough for SMA50

TRADE_SIZE_USD = 50.0          # USD per trade
MIN_BALANCE_RESERVE = 20.0     # keep minimum reserve
CYCLE_INTERVAL_MINUTES = 15

# Sentiment thresholds
BEARISH_THRESHOLD = 65   # confidence % to trigger bearish signal
BULLISH_THRESHOLD = 65   # confidence % to trigger bullish signal

# ---------------------------------------------------------------------------
# Logging  (logs are stored in-memory for dashboard consumption)
# ---------------------------------------------------------------------------
LOG_BUFFER = []
MAX_LOG_LINES = 200

class BufferHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        LOG_BUFFER.append(msg)
        if len(LOG_BUFFER) > MAX_LOG_LINES:
            LOG_BUFFER.pop(0)

logger = logging.getLogger("master_engine")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

console = logging.StreamHandler(sys.stdout)
console.setFormatter(fmt)
logger.addHandler(console)

buf_handler = BufferHandler()
buf_handler.setFormatter(fmt)
logger.addHandler(buf_handler)

# ---------------------------------------------------------------------------
# Exchange + Supabase clients (lazy init)
# ---------------------------------------------------------------------------
exchange: ccxt.gemini = None  # type: ignore
supabase: Client = None       # type: ignore


def init_exchange():
    """Initialize Gemini exchange via ccxt with margin support."""
    global exchange
    if exchange is not None:
        return
    exchange = ccxt.gemini({
        "apiKey": GEMINI_API_KEY,
        "secret": GEMINI_API_SECRET,
        "enableRateLimit": True,
        "options": {
            "defaultType": "margin",  # use margin account
        },
    })
    exchange.set_sandbox_mode(False)
    logger.info("✅ Gemini exchange initialized (margin mode)")


def init_supabase():
    """Initialize Supabase client."""
    global supabase
    if supabase is not None:
        return
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("⚠️  Supabase credentials not set – running in local-only mode")
        return
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized")


# ---------------------------------------------------------------------------
# Supabase helpers  (single source of truth)
# ---------------------------------------------------------------------------

def sb_get_balance() -> float:
    """Read latest balance from Supabase equity table."""
    if supabase is None:
        return _exchange_balance()
    try:
        resp = supabase.table("equity").select("*").order("created_at", desc=True).limit(1).execute()
        if resp.data:
            return float(resp.data[0].get("balance", 0))
    except Exception as e:
        logger.error(f"Supabase balance read error: {e}")
    return _exchange_balance()


def sb_update_balance(balance: float):
    """Insert new balance snapshot into Supabase."""
    if supabase is None:
        return
    try:
        supabase.table("equity").insert({
            "balance": balance,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Supabase balance write error: {e}")


def sb_get_positions() -> list:
    """Read active positions from Supabase."""
    if supabase is None:
        return []
    try:
        resp = (supabase.table("positions")
                .select("*")
                .eq("status", "open")
                .execute())
        return resp.data or []
    except Exception as e:
        logger.error(f"Supabase positions read error: {e}")
        return []


def sb_open_position(symbol: str, side: str, qty: float, entry_price: float):
    """Record a new open position in Supabase."""
    if supabase is None:
        return
    try:
        supabase.table("positions").insert({
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entry_price": entry_price,
            "status": "open",
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Supabase position open error: {e}")


def sb_close_position(position_id, exit_price: float, pnl: float):
    """Mark a position as closed in Supabase."""
    if supabase is None:
        return
    try:
        supabase.table("positions").update({
            "status": "closed",
            "exit_price": exit_price,
            "pnl": pnl,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", position_id).execute()
    except Exception as e:
        logger.error(f"Supabase position close error: {e}")


def sb_log_trade(symbol: str, side: str, qty: float, price: float, action: str, pnl: float = 0):
    """Log a trade event to Supabase."""
    if supabase is None:
        return
    try:
        supabase.table("trades").insert({
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "action": action,
            "pnl": pnl,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Supabase trade log error: {e}")


# ---------------------------------------------------------------------------
# Exchange helpers
# ---------------------------------------------------------------------------

def _exchange_balance() -> float:
    """Fetch USD balance from Gemini."""
    try:
        init_exchange()
        bal = exchange.fetch_balance()
        return float(bal.get("total", {}).get("USD", 0))
    except Exception as e:
        logger.error(f"Exchange balance error: {e}")
        return 0.0


def fetch_ohlcv(symbol: str) -> list:
    """Fetch OHLCV candles for a symbol."""
    try:
        init_exchange()
        candles = exchange.fetch_ohlcv(symbol, CANDLE_TIMEFRAME, limit=CANDLE_LIMIT)
        return candles
    except Exception as e:
        logger.error(f"OHLCV fetch error for {symbol}: {e}")
        return []


def fetch_ticker_price(symbol: str) -> float:
    """Get current price for a symbol."""
    try:
        init_exchange()
        ticker = exchange.fetch_ticker(symbol)
        return float(ticker["last"])
    except Exception as e:
        logger.error(f"Ticker fetch error for {symbol}: {e}")
        return 0.0


def calculate_sma(closes: list, period: int) -> float:
    """Calculate Simple Moving Average."""
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


# ---------------------------------------------------------------------------
# Technical analysis
# ---------------------------------------------------------------------------

def analyze_symbol(symbol: str) -> dict:
    """
    Run SMA20/SMA50 analysis on a symbol.
    Returns: {symbol, price, sma20, sma50, sentiment, confidence, analysis_text}
    """
    candles = fetch_ohlcv(symbol)
    price = fetch_ticker_price(symbol)
    tag = SYMBOL_MAP[symbol]

    if not candles or price == 0:
        return {
            "symbol": tag,
            "price": 0,
            "sma20": 0,
            "sma50": 0,
            "sentiment": "NEUTRAL",
            "confidence": 50,
            "analysis": f"Unable to fetch data for {tag}.",
        }

    closes = [c[4] for c in candles]  # close prices
    sma20 = calculate_sma(closes, SMA_SHORT)
    sma50 = calculate_sma(closes, SMA_LONG)

    # Determine sentiment & confidence
    sentiment, confidence, analysis = _evaluate_sma(tag, price, sma20, sma50)

    return {
        "symbol": tag,
        "price": price,
        "sma20": round(sma20, 3),
        "sma50": round(sma50, 3),
        "sentiment": sentiment,
        "confidence": confidence,
        "analysis": analysis,
    }


def _evaluate_sma(tag: str, price: float, sma20: float, sma50: float):
    """Evaluate SMA crossover & price position to derive sentiment."""
    if sma20 == 0 or sma50 == 0:
        return "NEUTRAL", 50, f"Insufficient data for {tag}."

    price_vs_sma20 = (price - sma20) / sma20 * 100
    price_vs_sma50 = (price - sma50) / sma50 * 100
    sma_spread = (sma20 - sma50) / sma50 * 100

    # Bearish: price below both SMAs
    if price < sma20 and price < sma50:
        dist = abs(price_vs_sma20) + abs(price_vs_sma50)
        conf = min(55 + int(dist * 3), 90)
        text = (
            f"{tag} price at ${price:,.2f} is below both SMA20 (${sma20:,.3f}) "
            f"and SMA50 (${sma50:,.3f}), indicating bearish momentum. "
            f"The price is below the short-term moving average (SMA20) by "
            f"approximately ${abs(price - sma20):,.2f} and below the medium-term "
            f"moving average (SMA50) by about ${abs(price - sma50):,.2f}. "
            f"This suggests selling pressure and potential downward continuation, "
            f"though the proximity to both SMAs (especially SMA50) limits confidence."
        )
        return "BEARISH", conf, text

    # Bullish: price above both SMAs
    if price > sma20 and price > sma50:
        dist = abs(price_vs_sma20) + abs(price_vs_sma50)
        conf = min(55 + int(dist * 3), 90)
        text = (
            f"{tag} at ${price:,.2f} is above both SMA20 (${sma20:,.3f}) "
            f"and SMA50 (${sma50:,.3f}), indicating bullish momentum. "
            f"Price is ${price - sma20:,.2f} above SMA20 and ${price - sma50:,.2f} "
            f"above SMA50, suggesting buying pressure and upward trend continuation."
        )
        return "BULLISH", conf, text

    # Neutral: price between the two SMAs or very close
    spread_pct = abs(price_vs_sma20) + abs(price_vs_sma50)
    conf = max(50, 55 + int(spread_pct))
    text = (
        f"{tag} at ${price:,.2f} is positioned between SMA20 "
        f"(${sma20:,.3f}) and SMA50 (${sma50:,.3f}), indicating a consolidation "
        f"phase. The price is slightly {'below' if price < sma20 else 'above'} SMA20 "
        f"but {'above' if price > sma50 else 'below'} SMA50, showing mixed signals "
        f"without clear momentum in either direction. The narrow gap between the "
        f"moving averages suggests low volatility and indecision in the market."
    )
    return "NEUTRAL", conf, text


# ---------------------------------------------------------------------------
# Trade execution with margin pre-checks
# ---------------------------------------------------------------------------

def check_margin_available(symbol: str, side: str, qty: float, price: float) -> bool:
    """
    Pre-check if we have enough margin/balance to execute the trade.
    Prevents 'insufficient funds' errors from Gemini.
    """
    try:
        init_exchange()
        balance = _exchange_balance()
        required = qty * price

        # For sells/shorts on margin, Gemini requires collateral
        # Use a conservative 50% margin requirement estimate
        margin_required = required * 0.5 if side == "sell" else required

        if balance < margin_required + MIN_BALANCE_RESERVE:
            logger.error(
                f"❌ [MARGIN CHECK] {symbol}: Need ${margin_required:.2f} + "
                f"${MIN_BALANCE_RESERVE:.2f} reserve, have ${balance:.2f}"
            )
            return False

        logger.info(
            f"✅ [MARGIN CHECK] {symbol}: ${margin_required:.2f} required, "
            f"${balance:.2f} available"
        )
        return True
    except Exception as e:
        logger.error(f"❌ [MARGIN CHECK] Error: {e}")
        return False


def get_min_order_size(symbol: str) -> float:
    """Get minimum order size for a symbol on Gemini."""
    min_sizes = {
        "BTC/USD": 0.00001,
        "ETH/USD": 0.001,
        "SOL/USD": 0.01,
        "LTC/USD": 0.01,
        "XRP/USD": 1.0,
        "DOGE/USD": 1.0,
    }
    return min_sizes.get(symbol, 0.001)


def calculate_order_qty(symbol: str, price: float, usd_amount: float) -> float:
    """Calculate order quantity from USD amount, respecting minimums."""
    if price <= 0:
        return 0.0
    raw_qty = usd_amount / price
    min_qty = get_min_order_size(symbol)
    if raw_qty < min_qty:
        logger.warning(f"⚠️  {symbol}: Calculated qty {raw_qty:.8f} < min {min_qty}")
        return 0.0
    # Round down to avoid over-ordering
    precision = len(str(min_qty).rstrip('0').split('.')[-1]) if '.' in str(min_qty) else 0
    qty = float(Decimal(str(raw_qty)).quantize(Decimal(str(min_qty)), rounding=ROUND_DOWN))
    return qty


def place_order(symbol: str, side: str, qty: float, price: float) -> dict:
    """
    Place a limit order on Gemini with comprehensive error handling.
    Returns order dict or None on failure.
    """
    tag = SYMBOL_MAP[symbol]
    try:
        init_exchange()

        # Pre-flight margin check
        if not check_margin_available(symbol, side, qty, price):
            logger.error(
                f"❌ [EXECUTION ERROR] {tag}: Failed to place {side} order on "
                f"symbol '{tag}' for price ${price:,.2f} and quantity {qty} "
                f"{symbol.split('/')[0]} due to insufficient funds"
            )
            return None

        logger.info(f"🚀 Placing {side.upper()} order: {tag} | qty: {qty} @ {price}")

        order = exchange.create_order(
            symbol=symbol,
            type="exchange limit",
            side=side,
            amount=qty,
            price=price,
        )

        logger.info(f"✅ Order placed: {tag} {side.upper()} {qty} @ ${price:,.2f}")
        sb_log_trade(tag, side, qty, price, "open")
        return order

    except ccxt.InsufficientFunds as e:
        logger.error(
            f"❌ [EXECUTION ERROR] {tag}: gemini Failed to place {side} order on "
            f"symbol '{tag}' for price ${price:,.2f} and quantity {qty} "
            f"{symbol.split('/')[0]} due to insufficient funds"
        )
        return None
    except ccxt.InvalidOrder as e:
        logger.error(f"❌ [EXECUTION ERROR] {tag}: Invalid order – {e}")
        return None
    except ccxt.NetworkError as e:
        logger.error(f"❌ [NETWORK ERROR] {tag}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ [EXECUTION ERROR] {tag}: {e}")
        return None


# ---------------------------------------------------------------------------
# Position management
# ---------------------------------------------------------------------------

def close_position(position: dict, current_price: float):
    """Close an existing position."""
    symbol_tag = position["symbol"]
    # Convert tag back to ccxt symbol
    symbol = None
    for s, tag in SYMBOL_MAP.items():
        if tag == symbol_tag:
            symbol = s
            break
    if not symbol:
        logger.error(f"Unknown symbol tag: {symbol_tag}")
        return

    side = position["side"]
    qty = float(position["qty"])
    entry = float(position["entry_price"])

    # Close = opposite side
    close_side = "sell" if side == "buy" else "buy"

    logger.info(f"🔴 CLOSED {side.upper()} {symbol_tag} successfully.")

    order = place_order(symbol, close_side, qty, current_price)

    if order:
        pnl = (current_price - entry) * qty if side == "buy" else (entry - current_price) * qty
        sb_close_position(position.get("id"), current_price, pnl)
        sb_log_trade(symbol_tag, close_side, qty, current_price, "close", pnl)
        logger.info(f"💰 PnL: ${pnl:+.2f}")
    else:
        logger.warning(f"⚠️  Failed to close {symbol_tag} position on exchange")


def open_new_position(symbol: str, side: str, price: float):
    """Open a new position with margin checks."""
    tag = SYMBOL_MAP[symbol]
    qty = calculate_order_qty(symbol, price, TRADE_SIZE_USD)

    if qty <= 0:
        logger.warning(f"⚠️  {tag}: Order qty too small, skipping")
        return

    logger.info(f"🚀 OPENING {side.upper()} on {tag} | qty: {qty} @ {price}")

    order = place_order(symbol, side, qty, price)
    if order:
        sb_open_position(tag, side, qty, price)


# ---------------------------------------------------------------------------
# Signal logic  (flip detection)
# ---------------------------------------------------------------------------

def determine_action(sentiment: str, confidence: int) -> str:
    """
    Map sentiment + confidence to a trading action.
    Returns: 'BUY', 'SHORT', 'HOLD'
    """
    if sentiment == "BULLISH" and confidence >= BULLISH_THRESHOLD:
        return "BUY"
    elif sentiment == "BEARISH" and confidence >= BEARISH_THRESHOLD:
        return "SHORT"
    return "HOLD"


def process_signal(symbol: str, analysis: dict, positions: list):
    """
    Decide whether to open/close/flip a position based on the new signal.
    """
    tag = analysis["symbol"]
    action = determine_action(analysis["sentiment"], analysis["confidence"])
    price = analysis["price"]

    # Find current position for this symbol
    current_pos = None
    for p in positions:
        if p["symbol"] == tag and p["status"] == "open":
            current_pos = p
            break

    current_side = current_pos["side"] if current_pos else None

    logger.info(f"[{tag}] {analysis['sentiment']} ({analysis['confidence']}%) -> {action}")

    # No position and HOLD -> do nothing
    if current_pos is None and action == "HOLD":
        return

    # No position and signal -> open
    if current_pos is None and action in ("BUY", "SHORT"):
        side = "buy" if action == "BUY" else "sell"
        open_new_position(symbol, side, price)
        return

    # Have position – check for flip or close
    if current_pos:
        if action == "BUY" and current_side == "buy":
            return  # already long
        if action == "SHORT" and current_side == "sell":
            return  # already short

        # Flip or close
        if action == "HOLD":
            logger.info(f"🔄 FLIP DETECTED: {current_side.upper()} -> HOLD. Closing old position first...")
            close_position(current_pos, price)
            return

        if (action == "BUY" and current_side == "sell") or (action == "SHORT" and current_side == "buy"):
            old_action = current_side.upper()
            new_action = action
            logger.info(f"🔄 FLIP DETECTED: {old_action} -> {new_action}. Closing old position first...")
            close_position(current_pos, price)

            # Wait for exchange to settle
            logger.info("⏳ Waiting 3s for exchange to settle balance...")
            time.sleep(3)

            side = "buy" if action == "BUY" else "sell"
            open_new_position(symbol, side, price)


# ---------------------------------------------------------------------------
# Main analysis cycle
# ---------------------------------------------------------------------------

# Shared state for dashboard
LATEST_ANALYSIS = {}
LATEST_BALANCE = 0.0


def run_cycle():
    """Run one full analysis + trading cycle."""
    global LATEST_ANALYSIS, LATEST_BALANCE

    logger.info("=" * 60)
    logger.info("🔄 Starting analysis cycle...")
    logger.info("=" * 60)

    try:
        init_exchange()
        init_supabase()
    except Exception as e:
        logger.error(f"Init error: {e}")
        return

    # Refresh balance
    LATEST_BALANCE = sb_get_balance()
    logger.info(f"💰 Current balance: ${LATEST_BALANCE:,.2f}")

    # Refresh positions from Supabase
    positions = sb_get_positions()
    logger.info(f"📊 Active positions: {len(positions)}")

    analyses = {}

    for symbol in SYMBOLS:
        tag = SYMBOL_MAP[symbol]
        try:
            analysis = analyze_symbol(symbol)
            analyses[tag] = analysis
            process_signal(symbol, analysis, positions)
        except Exception as e:
            logger.error(f"Error processing {tag}: {e}")
            logger.error(traceback.format_exc())

    LATEST_ANALYSIS = analyses

    # Update balance after trades
    new_balance = _exchange_balance()
    if new_balance > 0:
        sb_update_balance(new_balance)
        LATEST_BALANCE = new_balance

    logger.info(f"✅ Cycle complete. Balance: ${LATEST_BALANCE:,.2f}")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def start_engine():
    """Start the engine with scheduled cycles."""
    logger.info("=" * 60)
    logger.info("  MASTER ENGINE v2.1 (DEBUG MODE)")
    logger.info("=" * 60)
    logger.info(f"Symbols: {', '.join(SYMBOL_MAP.values())}")
    logger.info(f"Cycle interval: {CYCLE_INTERVAL_MINUTES} minutes")
    logger.info(f"Trade size: ${TRADE_SIZE_USD}")
    logger.info("")

    # Initial cycle
    run_cycle()

    # Schedule subsequent cycles
    schedule.every(CYCLE_INTERVAL_MINUTES).minutes.do(run_cycle)

    logger.info(f"⏰ Next cycle in {CYCLE_INTERVAL_MINUTES} minutes. Waiting...")
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    start_engine()
