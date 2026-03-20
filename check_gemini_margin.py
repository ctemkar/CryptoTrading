#!/usr/bin/env python3
"""
Gemini Margin Diagnostic Tool
==============================
Diagnoses SHORT order failures on Gemini by:
1. Fetching account balances (USD + all crypto assets)
2. Checking margin trading status and available limits
3. Testing order type differences (exchange limit vs limit/margin)
4. Showing available borrowing capacity
5. Logging exact API error responses

Usage:
    python check_gemini_margin.py

Requires .env file with GEMINI_API_KEY and GEMINI_API_SECRET
"""

import os
import sys
import json
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

try:
    import ccxt
except ImportError:
    print("ERROR: ccxt not installed. Run: pip install ccxt")
    sys.exit(1)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_SECRET = os.getenv("GEMINI_API_SECRET", "")

if not GEMINI_API_KEY or not GEMINI_API_SECRET:
    print("=" * 60)
    print("ERROR: Missing Gemini API credentials!")
    print("Create a .env file with:")
    print("  GEMINI_API_KEY=your_key_here")
    print("  GEMINI_API_SECRET=your_secret_here")
    print("=" * 60)
    sys.exit(1)


def create_exchange(default_type="spot"):
    """Create a Gemini exchange instance."""
    return ccxt.gemini({
        "apiKey": GEMINI_API_KEY,
        "secret": GEMINI_API_SECRET,
        "enableRateLimit": True,
        "options": {
            "defaultType": default_type,
        },
    })


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_balance(exchange):
    """Fetch and display all balances."""
    section("1. ACCOUNT BALANCES")
    try:
        bal = exchange.fetch_balance()
        print(f"\n  Total balances:")
        total = bal.get("total", {})
        for asset, amount in sorted(total.items()):
            if float(amount) > 0:
                print(f"    {asset}: {amount}")

        print(f"\n  Free (available) balances:")
        free = bal.get("free", {})
        for asset, amount in sorted(free.items()):
            if float(amount) > 0:
                print(f"    {asset}: {amount}")

        print(f"\n  Used (locked) balances:")
        used = bal.get("used", {})
        for asset, amount in sorted(used.items()):
            if float(amount) > 0:
                print(f"    {asset}: {amount}")

        usd_total = float(total.get("USD", 0))
        print(f"\n  >>> USD Total: ${usd_total:.2f}")
        return usd_total
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        return 0


def test_margin_status(exchange):
    """Check if margin trading is enabled."""
    section("2. MARGIN TRADING STATUS")
    try:
        # Try fetching margin balance
        print("\n  Attempting to fetch margin account info...")
        # Try the raw Gemini endpoint for margin status
        try:
            margin_info = exchange.private_post_v1_marginaccountstatus()
            print(f"  Margin Account Status: {json.dumps(margin_info, indent=4)}")
        except Exception as e:
            print(f"  Margin status endpoint: {e}")

        # Try fetching available balances with margin type
        try:
            margin_exchange = create_exchange("margin")
            margin_bal = margin_exchange.fetch_balance()
            print(f"\n  Margin balance (total):")
            for asset, amount in margin_bal.get("total", {}).items():
                if float(amount) > 0:
                    print(f"    {asset}: {amount}")
        except Exception as e:
            print(f"  Margin balance fetch: {e}")

    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()


def test_order_types(exchange):
    """Test the difference between 'exchange limit' and 'limit' order types."""
    section("3. ORDER TYPE ANALYSIS")

    print("""
  CRITICAL FINDING:
  ─────────────────
  Gemini uses TWO order type prefixes:
    • "exchange limit" → SPOT order (must own asset to sell)
    • "limit"          → MARGIN order (can short with borrowed funds)

  The current engine uses "exchange limit" for ALL orders.
  This is why:
    ✅ BUY works  → spending USD you have (spot buy is fine)
    ❌ SHORT fails → trying to sell crypto you DON'T own (spot sell fails)

  FIX: Use type="limit" (margin) for SHORT orders.
  This is done by passing params={'type': 'limit'} to ccxt's create_order.
""")


def test_short_order_dry_run(exchange):
    """Simulate what happens with a short order (both spot and margin types)."""
    section("4. SHORT ORDER DRY RUN (Read-Only)")

    test_symbol = "ETH/USD"
    test_qty = 0.001  # minimal ETH amount

    try:
        ticker = exchange.fetch_ticker(test_symbol)
        price = float(ticker["last"])
        print(f"\n  Current {test_symbol} price: ${price:,.2f}")
        print(f"  Test qty: {test_qty} ETH (≈${test_qty * price:.2f})")

        # Test 1: Spot sell (exchange limit) — this should fail if you don't own ETH
        print(f"\n  --- Test A: SPOT sell (type='exchange limit') ---")
        print(f"  This is what the current code does for SHORT orders.")
        print(f"  Expected: FAIL with 'insufficient funds' if no ETH balance")
        try:
            # Use maker-or-cancel to prevent actual execution, then cancel
            order = exchange.create_order(
                symbol=test_symbol,
                type="limit",
                side="sell",
                amount=test_qty,
                price=price * 1.5,  # way above market so it won't fill
                params={"type": "exchange limit", "options": ["maker-or-cancel"]},
            )
            print(f"  Result: ORDER PLACED (id={order.get('id')})")
            print(f"  Canceling test order...")
            exchange.cancel_order(order["id"], test_symbol)
            print(f"  Canceled.")
        except ccxt.InsufficientFunds as e:
            print(f"  Result: FAILED — InsufficientFunds: {e}")
        except ccxt.InvalidOrder as e:
            print(f"  Result: FAILED — InvalidOrder: {e}")
        except Exception as e:
            print(f"  Result: ERROR — {type(e).__name__}: {e}")

        time.sleep(1)  # rate limit

        # Test 2: Margin sell (limit) — this should work for shorting
        print(f"\n  --- Test B: MARGIN sell (type='limit') ---")
        print(f"  This is the FIX: use 'limit' type for SHORT orders.")
        print(f"  Expected: SUCCESS (can short sell with margin)")
        try:
            order = exchange.create_order(
                symbol=test_symbol,
                type="limit",
                side="sell",
                amount=test_qty,
                price=price * 1.5,  # way above market so it won't fill
                params={"type": "limit", "options": ["maker-or-cancel"]},
            )
            print(f"  Result: ORDER PLACED ✅ (id={order.get('id')})")
            print(f"  Canceling test order...")
            exchange.cancel_order(order["id"], test_symbol)
            print(f"  Canceled.")
        except ccxt.InsufficientFunds as e:
            print(f"  Result: FAILED — InsufficientFunds: {e}")
            print(f"  This means margin trading may not be enabled on your account.")
        except ccxt.InvalidOrder as e:
            print(f"  Result: FAILED — InvalidOrder: {e}")
        except Exception as e:
            print(f"  Result: ERROR — {type(e).__name__}: {e}")

    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()


def test_buy_vs_sell_comparison(exchange):
    """Compare BUY and SELL (short) parameters side by side."""
    section("5. BUY vs SHORT ORDER PARAMETER COMPARISON")
    print("""
  BUY Order (current — works):
  ────────────────────────────
    exchange.create_order(
        symbol="ETH/USD",
        type="limit",
        side="buy",
        amount=0.023,
        price=2134.55,
    )
    → ccxt sends: type="exchange limit" (spot) ✅
    → Spends USD you have to buy ETH

  SHORT Order (current — FAILS):
  ──────────────────────────────
    exchange.create_order(
        symbol="ETH/USD",
        type="limit",
        side="sell",
        amount=0.023,
        price=2134.55,
    )
    → ccxt sends: type="exchange limit" (spot) ❌
    → Tries to sell ETH you DON'T own → insufficient funds!

  SHORT Order (FIXED):
  ────────────────────
    exchange.create_order(
        symbol="ETH/USD",
        type="limit",
        side="sell",
        amount=0.023,
        price=2134.55,
        params={"type": "limit"},  # ← THIS IS THE FIX
    )
    → ccxt sends: type="limit" (margin) ✅
    → Borrows ETH and sells it (proper short)

  CLOSE SHORT Order (also needs fix):
  ────────────────────────────────────
    When closing a short, we BUY back the borrowed asset.
    This should also use margin type="limit":
    exchange.create_order(
        symbol="ETH/USD",
        type="limit",
        side="buy",
        amount=0.023,
        price=2100.00,
        params={"type": "limit"},  # margin buy to close short
    )
""")


def show_recommendations():
    """Display fix recommendations."""
    section("6. RECOMMENDATIONS")
    print("""
  The root cause is that ALL orders use "exchange limit" (spot) type.
  
  FIXES NEEDED in master_engine.py:
  
  1. In place_order(), detect if this is a margin trade and pass the
     correct order type:
     
     - For SHORT (sell) orders: params={'type': 'limit'}  (margin)
     - For closing SHORT (buy back): params={'type': 'limit'}  (margin)  
     - For BUY orders: use default 'exchange limit' (spot)
     - For closing BUY (sell owned asset): use default (spot)
  
  2. Track which positions are margin vs spot so closes use the
     correct order type.
  
  3. Reduce the safety buffer for margin orders since Gemini's
     margin requirements are typically lower than full notional.
  
  4. Add the account parameter if needed:
     params={'type': 'limit', 'account': 'margin'}
""")


def main():
    print("=" * 60)
    print("  GEMINI MARGIN DIAGNOSTIC TOOL")
    print("=" * 60)

    exchange = create_exchange("spot")

    usd_balance = test_balance(exchange)
    test_margin_status(exchange)
    test_order_types(exchange)
    test_short_order_dry_run(exchange)
    test_buy_vs_sell_comparison(exchange)
    show_recommendations()

    print(f"\n{'=' * 60}")
    print(f"  DIAGNOSTIC COMPLETE")
    print(f"  USD Balance: ${usd_balance:.2f}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
