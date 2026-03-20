#!/usr/bin/env python3
"""
Gemini Margin Diagnostic Tool
==============================
Diagnoses SHORT order failures on Gemini by:
1. Fetching account balances (USD + all crypto assets)
2. Checking margin trading status and available limits
3. Testing the correct margin_order parameter
4. Showing the difference between spot and margin orders
5. Logging exact API error responses

ROOT CAUSE (discovered 2026-03-21):
  ccxt's gemini.create_order() ALWAYS sets request['type'] = 'exchange limit'.
  Passing params={'type': 'limit'} is USELESS — ccxt extracts and strips the
  'type' key from params before sending to Gemini.

  The CORRECT approach: pass params={'margin_order': True} which goes straight
  through to the Gemini API payload, enabling margin (short-selling).

  See: https://docs.gemini.com/rest/orders — margin_order parameter.

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


def create_exchange():
    """Create a Gemini exchange instance."""
    return ccxt.gemini({
        "apiKey": GEMINI_API_KEY,
        "secret": GEMINI_API_SECRET,
        "enableRateLimit": True,
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
        # Try fetching margin account status via Gemini API
        print("\n  Attempting to fetch margin account info...")
        try:
            margin_info = exchange.private_post_v1_marginaccountstatus()
            print(f"  Margin Account Status: {json.dumps(margin_info, indent=4)}")
        except Exception as e:
            print(f"  Margin status endpoint: {e}")

        # Try risk stats
        try:
            risk = exchange.private_post_v1_risk_stats()
            print(f"\n  Risk Stats: {json.dumps(risk, indent=4)}")
        except Exception as e:
            print(f"  Risk stats endpoint: {e}")

    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()


def explain_root_cause():
    """Explain the root cause of SHORT failures."""
    section("3. ROOT CAUSE ANALYSIS")
    print("""
  THE BUG:
  ────────
  Previous code used: params={'type': 'limit'} for margin orders.
  
  BUT ccxt's gemini.create_order() does this internally:
    1. Sets request['type'] = 'exchange limit'     (always)
    2. type = safe_string(params, 'type', type)     (reads 'type' from params)
    3. params = omit(params, 'type')                (REMOVES 'type' from params!)
    4. extend(request, params)                      (merges remaining params)
  
  Result: params={'type': 'limit'} is read into a local variable,
  stripped from params, and NEVER applied to the request!
  The request always sends type='exchange limit' (spot order).
  
  THE FIX:
  ────────
  Use params={'margin_order': True} instead.
  
  This parameter is NOT stripped by ccxt — it passes through directly
  to the Gemini API. From docs.gemini.com/rest/orders:
    "margin_order: true — designates this as a margin order"
  
  This enables short selling (selling crypto you don't own) by
  borrowing the asset through Gemini's margin facility.
""")


def test_short_order(exchange):
    """Test SHORT order with margin_order=True vs without."""
    section("4. SHORT ORDER TEST")

    test_symbol = "ETH/USD"
    test_qty = 0.001  # minimal ETH amount

    try:
        ticker = exchange.fetch_ticker(test_symbol)
        price = float(ticker["last"])
        test_price = round(price * 1.5, 2)  # way above market — won't fill
        print(f"\n  Current {test_symbol} price: ${price:,.2f}")
        print(f"  Test qty: {test_qty} ETH (≈${test_qty * price:.2f})")
        print(f"  Test sell price: ${test_price} (150% above market — won't fill)")

        # Test A: SPOT sell (default, no margin) — should FAIL if no ETH
        print(f"\n  --- Test A: SPOT sell (no margin_order param) ---")
        print(f"  Expected: FAIL with 'insufficient funds' (no ETH to sell)")
        try:
            order = exchange.create_order(
                symbol=test_symbol,
                type="limit",
                side="sell",
                amount=test_qty,
                price=test_price,
                params={"options": ["maker-or-cancel"]},
            )
            print(f"  Result: ORDER PLACED (id={order.get('id')})")
            exchange.cancel_order(order["id"], test_symbol)
            print(f"  Canceled.")
        except ccxt.InsufficientFunds as e:
            print(f"  Result: ❌ InsufficientFunds (expected!): {e}")
        except Exception as e:
            print(f"  Result: ❌ {type(e).__name__}: {e}")

        time.sleep(1)  # rate limit

        # Test B: MARGIN sell (margin_order=True) — should SUCCEED
        print(f"\n  --- Test B: MARGIN sell (margin_order=True) ---")
        print(f"  Expected: SUCCESS (borrows ETH via margin to short-sell)")
        try:
            order = exchange.create_order(
                symbol=test_symbol,
                type="limit",
                side="sell",
                amount=test_qty,
                price=test_price,
                params={"margin_order": True, "options": ["maker-or-cancel"]},
            )
            print(f"  Result: ✅ ORDER PLACED (id={order.get('id')})")
            otype = order.get("info", {}).get("type", "unknown")
            print(f"  Gemini order type: {otype}")
            exchange.cancel_order(order["id"], test_symbol)
            print(f"  Canceled test order.")
        except ccxt.InsufficientFunds as e:
            print(f"  Result: ❌ InsufficientFunds: {e}")
            print(f"  → Margin may not be enabled on this account, or")
            print(f"  → Insufficient USD collateral for margin.")
        except Exception as e:
            print(f"  Result: ❌ {type(e).__name__}: {e}")

        time.sleep(1)

        # Test C: OLD broken approach (params={'type': 'limit'}) — will behave like spot
        print(f"\n  --- Test C: OLD broken approach (params={{'type': 'limit'}}) ---")
        print(f"  Expected: FAIL (ccxt strips 'type' from params, sends as spot)")
        try:
            order = exchange.create_order(
                symbol=test_symbol,
                type="limit",
                side="sell",
                amount=test_qty,
                price=test_price,
                params={"type": "limit", "options": ["maker-or-cancel"]},
            )
            print(f"  Result: ORDER PLACED (id={order.get('id')})")
            exchange.cancel_order(order["id"], test_symbol)
            print(f"  Canceled.")
        except ccxt.InsufficientFunds as e:
            print(f"  Result: ❌ InsufficientFunds (as expected — same as spot!)")
        except Exception as e:
            print(f"  Result: ❌ {type(e).__name__}: {e}")

    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()


def show_fix_summary():
    """Display the fix applied to master_engine.py."""
    section("5. FIX SUMMARY")
    print("""
  CHANGE in master_engine.py → place_order():
  
  BEFORE (broken):
  ────────────────
    order_params = {}
    if use_margin:
        order_params["type"] = "limit"        # ← STRIPPED by ccxt!
    
    exchange.create_order(
        symbol=symbol, type="limit", side=side,
        amount=qty, price=price,
        params=order_params,
    )
  
  AFTER (fixed):
  ──────────────
    order_params = {}
    if use_margin:
        order_params["margin_order"] = True    # ← Passes through to Gemini API
    
    exchange.create_order(
        symbol=symbol, type="limit", side=side,
        amount=qty, price=price,
        params=order_params,
    )
  
  ALSO:
  - Removed 'defaultType': 'margin' from exchange init (has no effect)
  - Updated docstrings to document the correct Gemini margin mechanism
""")


def main():
    print("=" * 60)
    print("  GEMINI MARGIN DIAGNOSTIC TOOL")
    print("  Updated: 2026-03-21 — margin_order fix")
    print("=" * 60)

    exchange = create_exchange()

    usd_balance = test_balance(exchange)
    test_margin_status(exchange)
    explain_root_cause()
    test_short_order(exchange)
    show_fix_summary()

    print(f"\n{'=' * 60}")
    print(f"  DIAGNOSTIC COMPLETE")
    print(f"  USD Balance: ${usd_balance:.2f}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
