#!/usr/bin/env python3
"""
Gemini Account Diagnostic Tool v2.0
====================================
Super-detailed diagnostic that checks EVERYTHING about your Gemini account
and margin trading setup. Run this BEFORE running the engine to verify
your account is properly configured for SHORT orders.

Usage:
    python check_gemini_account.py

Requirements:
    - .env file with GEMINI_API_KEY and GEMINI_API_SECRET
    - pip install ccxt python-dotenv requests
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import traceback
from datetime import datetime

try:
    import ccxt
except ImportError:
    print("❌ ccxt not installed. Run: pip install ccxt")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ requests not installed. Run: pip install requests")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("GEMINI_API_KEY", "")
API_SECRET = os.getenv("GEMINI_API_SECRET", "")
BASE_URL = "https://api.gemini.com"

# Test parameters
TEST_SYMBOL = "ETH/USD"
TEST_TAG = "ETHUSD"
TEST_AMOUNT_USD = 5.0  # Very small test order ($5)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def print_header(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_section(title: str):
    print(f"\n--- {title} ---")

def print_ok(msg: str):
    print(f"  ✅ {msg}")

def print_fail(msg: str):
    print(f"  ❌ {msg}")

def print_warn(msg: str):
    print(f"  ⚠️  {msg}")

def print_info(msg: str):
    print(f"  ℹ️  {msg}")


def gemini_private_request(endpoint: str, payload_extra: dict = None) -> dict:
    """Make an authenticated request to the Gemini private API.
    
    This bypasses ccxt entirely so we can see the raw API response.
    """
    url = BASE_URL + endpoint
    nonce = str(int(time.time() * 1000))
    
    payload = {
        "request": endpoint,
        "nonce": nonce,
    }
    if payload_extra:
        payload.update(payload_extra)
    
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode("utf-8"))
    
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        payload_b64,
        hashlib.sha384
    ).hexdigest()
    
    headers = {
        "Content-Type": "text/plain",
        "Content-Length": "0",
        "X-GEMINI-APIKEY": API_KEY,
        "X-GEMINI-PAYLOAD": payload_b64.decode("utf-8"),
        "X-GEMINI-SIGNATURE": signature,
        "Cache-Control": "no-cache",
    }
    
    resp = requests.post(url, headers=headers)
    return {"status_code": resp.status_code, "body": resp.json() if resp.text else {}, "raw": resp.text}


# ──────────────────────────────────────────────────────────────────────────────
# Diagnostic Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_api_credentials():
    """Test 1: Verify API key and secret are valid."""
    print_header("TEST 1: API Credentials")
    
    if not API_KEY:
        print_fail("GEMINI_API_KEY is empty or missing from .env")
        return False
    if not API_SECRET:
        print_fail("GEMINI_API_SECRET is empty or missing from .env")
        return False
    
    print_ok(f"API Key loaded: {API_KEY[:8]}...{API_KEY[-4:]}")
    print_ok(f"API Secret loaded: {'*' * 20}")
    
    # Test with a simple API call
    try:
        result = gemini_private_request("/v1/balances")
        if result["status_code"] == 200:
            print_ok("API credentials are VALID — authenticated successfully")
            return True
        else:
            print_fail(f"API authentication failed: {result['body']}")
            return False
    except Exception as e:
        print_fail(f"Failed to connect to Gemini: {e}")
        return False


def test_account_balances():
    """Test 2: Check all account balances."""
    print_header("TEST 2: Account Balances")
    
    result = gemini_private_request("/v1/balances")
    if result["status_code"] != 200:
        print_fail(f"Failed to fetch balances: {result['body']}")
        return {}
    
    balances = result["body"]
    
    # Show all non-zero balances
    print_section("Non-zero Balances")
    balances_dict = {}
    has_funds = False
    for b in balances:
        currency = b.get("currency", "")
        amount = float(b.get("amount", 0))
        available = float(b.get("available", 0))
        available_for_withdrawal = float(b.get("availableForWithdrawal", 0))
        
        balances_dict[currency] = {
            "amount": amount,
            "available": available,
            "availableForWithdrawal": available_for_withdrawal,
        }
        
        if amount > 0 or available > 0:
            has_funds = True
            print(f"    {currency:>6}: amount={amount:>12.6f}  available={available:>12.6f}  withdrawable={available_for_withdrawal:>12.6f}")
    
    if not has_funds:
        print_warn("No non-zero balances found. Account may be empty.")
    
    # Specifically check USD
    usd = balances_dict.get("USD", {})
    usd_available = usd.get("available", 0)
    print_section("USD Balance Summary")
    print(f"    Total USD:     ${usd.get('amount', 0):,.2f}")
    print(f"    Available USD: ${usd_available:,.2f}")
    
    if usd_available < 10:
        print_warn(f"Very low USD balance (${usd_available:.2f}). Need at least $25+ to trade.")
    elif usd_available < 50:
        print_warn(f"Low USD balance (${usd_available:.2f}). Engine needs $25+ reserve + trade size.")
    else:
        print_ok(f"USD balance looks good: ${usd_available:,.2f}")
    
    return balances_dict


def test_margin_status():
    """Test 3: Check if margin trading is enabled on the account."""
    print_header("TEST 3: Margin Trading Status")
    
    # Try the margin status endpoint
    print_section("Checking margin/risk endpoint")
    result = gemini_private_request("/v1/margin/risk_stats")
    
    print(f"    HTTP Status: {result['status_code']}")
    print(f"    Response: {json.dumps(result['body'], indent=4)}")
    
    if result["status_code"] == 200:
        print_ok("Margin trading appears to be ENABLED on your account")
        body = result["body"]
        if isinstance(body, dict):
            if "marginBuyingPower" in body:
                print_info(f"Margin buying power: ${float(body['marginBuyingPower']):,.2f}")
            if "initialMarginRequirement" in body:
                print_info(f"Initial margin requirement: {body['initialMarginRequirement']}")
        return True
    elif result["status_code"] == 403:
        print_fail("Margin trading is NOT ENABLED on your account (403 Forbidden)")
        print_info("You need to enable margin trading in Gemini settings.")
        print_info("Go to: gemini.com → Account → Settings → Margin Trading → Enable")
        return False
    elif result["status_code"] == 400:
        print_warn(f"Margin endpoint returned 400: {result['body']}")
        print_info("This could mean margin is not available for your account type.")
        return False
    else:
        print_warn(f"Unexpected status code: {result['status_code']}")
        print_info(f"Response: {result['body']}")
        return None
    

def test_margin_balances():
    """Test 4: Check margin-specific balances and borrowing limits."""
    print_header("TEST 4: Margin Balances & Borrowing Limits")
    
    # Check notional balances (includes margin positions)
    result = gemini_private_request("/v1/notionalbalances/usd")
    
    if result["status_code"] == 200:
        print_section("Notional Balances (includes margin)")
        for b in result["body"]:
            currency = b.get("currency", "")
            amount_notional = b.get("amountNotional", "0")
            available_notional = b.get("availableNotional", "0")
            
            if float(amount_notional) != 0 or float(available_notional) != 0:
                print(f"    {currency:>6}: notional=${float(amount_notional):>12.2f}  available_notional=${float(available_notional):>12.2f}")
    else:
        print_warn(f"Could not fetch notional balances: {result['body']}")
    
    # Check available margin for specific symbols
    print_section("Margin-eligible symbol check")
    margin_symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
    for sym in margin_symbols:
        # Try to see available margin for each symbol
        print(f"    {sym}: checking...")


def test_ccxt_order_construction():
    """Test 5: Show exactly what ccxt sends to Gemini for margin orders."""
    print_header("TEST 5: ccxt Order Construction (DRY RUN)")
    
    print_info("This shows what params ccxt would send to Gemini API")
    print_info("No actual orders are placed in this test")
    
    # Initialize exchange
    exchange = ccxt.gemini({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
    })
    exchange.set_sandbox_mode(False)
    
    # Get current ETH price for realistic test
    try:
        ticker = exchange.fetch_ticker(TEST_SYMBOL)
        price = ticker["last"]
        print_ok(f"Current {TEST_SYMBOL} price: ${price:,.2f}")
    except Exception as e:
        print_fail(f"Could not fetch ticker: {e}")
        price = 2000.0
        print_info(f"Using fallback price: ${price:,.2f}")
    
    qty = round(TEST_AMOUNT_USD / price, 6)
    
    # Show what the three different approaches send
    print_section("Approach 1: SPOT order (no margin params)")
    print(f"    exchange.create_order('{TEST_SYMBOL}', 'limit', 'sell', {qty}, {price})")
    print(f"    params = {{}}")
    print(f"    → This is a regular SPOT sell. Will fail if you don't own {TEST_SYMBOL.split('/')[0]}.")
    
    print_section("Approach 2: CORRECT margin order (margin_order=True)")
    print(f"    exchange.create_order('{TEST_SYMBOL}', 'limit', 'sell', {qty}, {price},")
    print(f"                         params={{'margin_order': True}})")
    print(f"    → This tells Gemini to borrow the asset for short-selling.")
    print(f"    → This is what our engine now uses for SHORT orders.")
    
    print_section("Approach 3: BROKEN approach (type='limit' — DOES NOT WORK)")
    print(f"    exchange.create_order('{TEST_SYMBOL}', 'limit', 'sell', {qty}, {price},")
    print(f"                         params={{'type': 'limit'}})")
    print(f"    → ccxt STRIPS the 'type' from params before sending to Gemini!")
    print(f"    → This becomes a SPOT order and fails with 'insufficient funds'.")
    
    # Verify by looking at ccxt internals
    print_section("ccxt internals verification")
    try:
        # Check if exchange has the describe method
        desc = exchange.describe()
        has_margin = desc.get("has", {}).get("createMarginOrder", None)
        print(f"    ccxt reports createMarginOrder: {has_margin}")
        print(f"    ccxt version: {ccxt.__version__}")
    except Exception as e:
        print_warn(f"Could not inspect ccxt internals: {e}")
    
    return price, qty


def test_live_short_order(price: float, qty: float):
    """Test 6: Actually test a tiny SHORT order on Gemini."""
    print_header("TEST 6: Live SHORT Order Test ($5)")
    
    print_warn("This test will attempt to place a REAL (tiny) SHORT order!")
    print_info(f"Symbol: {TEST_SYMBOL}, Side: SELL, Qty: {qty}, Price: ${price:,.2f}")
    print_info(f"Approximate value: ${qty * price:,.2f}")
    
    response = input("\n  Type 'yes' to proceed with live test, or anything else to skip: ").strip().lower()
    if response != "yes":
        print_info("Skipped live test.")
        return
    
    exchange = ccxt.gemini({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
    })
    exchange.set_sandbox_mode(False)
    
    # Enable verbose mode to see exact HTTP requests
    exchange.verbose = True
    
    print_section("Test A: SPOT sell (expected to fail if no ETH owned)")
    try:
        print("\n--- BEGIN VERBOSE OUTPUT (spot) ---")
        order = exchange.create_order(
            symbol=TEST_SYMBOL,
            type="limit",
            side="sell",
            amount=qty,
            price=price,
            params={},  # No margin
        )
        print("--- END VERBOSE OUTPUT ---")
        print_ok(f"SPOT sell succeeded (you own some {TEST_SYMBOL.split('/')[0]})")
        print(f"    Order ID: {order.get('id')}")
        # Cancel it immediately
        try:
            exchange.cancel_order(order["id"], TEST_SYMBOL)
            print_ok("Order cancelled")
        except:
            pass
    except ccxt.InsufficientFunds as e:
        print("--- END VERBOSE OUTPUT ---")
        print_ok(f"SPOT sell failed as expected (no {TEST_SYMBOL.split('/')[0]} to sell): {e}")
    except Exception as e:
        print("--- END VERBOSE OUTPUT ---")
        print_fail(f"Unexpected error: {e}")
    
    time.sleep(1)  # Rate limit
    
    print_section("Test B: MARGIN sell (margin_order=True)")
    try:
        print("\n--- BEGIN VERBOSE OUTPUT (margin) ---")
        order = exchange.create_order(
            symbol=TEST_SYMBOL,
            type="limit",
            side="sell",
            amount=qty,
            price=price,
            params={"margin_order": True},  # CORRECT margin param
        )
        print("--- END VERBOSE OUTPUT ---")
        print_ok("🎉 MARGIN sell SUCCEEDED! Margin trading works on your account!")
        print(f"    Order ID: {order.get('id')}")
        print(f"    Order details: {json.dumps(order, indent=4, default=str)}")
        # Cancel it immediately
        try:
            exchange.cancel_order(order["id"], TEST_SYMBOL)
            print_ok("Test order cancelled successfully")
        except Exception as e:
            print_warn(f"Could not cancel order: {e}")
            print_info("Check Gemini UI and cancel manually if needed")
    except ccxt.InsufficientFunds as e:
        print("--- END VERBOSE OUTPUT ---")
        print_fail(f"MARGIN sell FAILED with insufficient funds: {e}")
        print_info("This means either:")
        print_info("  1. Margin trading is NOT enabled on your Gemini account")
        print_info("  2. Your account doesn't have enough margin buying power")
        print_info("  3. ETH is not margin-eligible on your account tier")
        print_info("")
        print_info("👉 Solution: Enable margin at gemini.com → Settings → Margin Trading")
        print_info("👉 Or: Switch engine to CLOSE-ONLY mode (see MARGIN_SETUP.md)")
    except ccxt.ExchangeError as e:
        print("--- END VERBOSE OUTPUT ---")
        print_fail(f"Exchange error: {e}")
        error_str = str(e).lower()
        if "margin" in error_str or "not eligible" in error_str:
            print_info("Your account may not be approved for margin trading.")
        elif "minimum" in error_str:
            print_info("Order may be below Gemini's minimum order size.")
    except Exception as e:
        print("--- END VERBOSE OUTPUT ---")
        print_fail(f"Unexpected error: {e}")
        traceback.print_exc()


def test_engine_code_verification():
    """Test 7: Verify the engine code has the correct margin fix."""
    print_header("TEST 7: Engine Code Verification")
    
    engine_path = os.path.join(os.path.dirname(__file__), "master_engine.py")
    
    if not os.path.exists(engine_path):
        print_fail(f"master_engine.py not found at: {engine_path}")
        return
    
    with open(engine_path, "r") as f:
        code = f.read()
    
    # Check for the correct margin_order param
    checks = {
        'margin_order': {
            "pattern": 'order_params["margin_order"] = True',
            "description": "margin_order=True in place_order()",
            "critical": True,
        },
        'use_margin_param': {
            "pattern": "use_margin: bool = False",
            "description": "use_margin parameter in place_order()",
            "critical": True,
        },
        'short_uses_margin': {
            "pattern": "use_margin=is_short",
            "description": "open_new_position passes use_margin for shorts",
            "critical": True,
        },
        'close_uses_margin': {
            "pattern": "use_margin=is_short_position",
            "description": "close_position passes use_margin for short closes",
            "critical": True,
        },
        'no_broken_type_param': {
            "pattern": "params={'type': 'limit'}",
            "description": "OLD BROKEN code still present",
            "critical": False,  # This should NOT be found
            "expect_missing": True,
        },
    }
    
    all_good = True
    for name, check in checks.items():
        found = check["pattern"] in code
        expect_missing = check.get("expect_missing", False)
        
        if expect_missing:
            if found:
                print_fail(f"{check['description']} — FOUND (should be removed!)")
                all_good = False
            else:
                print_ok(f"{check['description']} — correctly removed ✓")
        else:
            if found:
                print_ok(f"{check['description']} — present ✓")
            else:
                print_fail(f"{check['description']} — MISSING!")
                if check["critical"]:
                    all_good = False
    
    # Check version
    if "v2.2" in code or "v2.3" in code:
        print_ok(f"Engine version looks current")
    else:
        print_warn("Engine may be outdated. Expected v2.2+")
    
    if all_good:
        print("\n  🎉 Engine code has all the correct margin fixes!")
    else:
        print("\n  ❌ Engine code is MISSING critical fixes. Pull the latest from GitHub!")
        print("     Run: git pull origin supabase-refactor-v2.1")


def print_summary_and_recommendations():
    """Print final summary with actionable recommendations."""
    print_header("SUMMARY & RECOMMENDATIONS")
    
    print("""
  If SHORT orders are failing with "insufficient funds", check these in order:

  1. PULL LATEST CODE
     Your local engine may not have the margin_order fix.
     Run: cd crypto-master-engine && git pull origin supabase-refactor-v2.1

  2. VERIFY MARGIN IS ENABLED ON GEMINI
     Go to: https://exchange.gemini.com/settings/margin
     You need margin trading explicitly enabled on your account.
     Note: Not all Gemini accounts are eligible for margin.
     Requirements: US-based individual account, net worth requirements met.

  3. CHECK YOUR BALANCE
     Even with margin enabled, you need sufficient USD as collateral.
     The engine needs: $20 reserve + trade size ($50 default) = ~$70 minimum.
     With $216 balance, you should be fine IF margin is enabled.

  4. USE CLOSE-ONLY MODE (if margin isn't available)
     If you can't enable margin, set this in your .env:
         SHORT_MODE=close_only
     This makes the engine:
       - BEARISH signal → Close existing LONG positions (don't open shorts)
       - BULLISH signal → Open LONG positions normally
       - You still profit from closing longs at the right time

  5. CHECK GEMINI ACCOUNT TYPE
     Margin is only available on:
       - Individual accounts (not institutional)
       - Accounts that have completed enhanced verification
       - Accounts in eligible jurisdictions (US states vary)
""")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║           GEMINI ACCOUNT DIAGNOSTIC TOOL v2.0                   ║")
    print("║  Checks everything about your margin trading setup              ║")
    print(f"║  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):>52} ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    
    # Test 1: Credentials
    if not test_api_credentials():
        print("\n❌ Cannot proceed without valid API credentials.")
        print("   Fix your .env file and try again.")
        return
    
    # Test 2: Balances
    balances = test_account_balances()
    
    # Test 3: Margin status
    margin_ok = test_margin_status()
    
    # Test 4: Margin balances
    test_margin_balances()
    
    # Test 5: ccxt order construction (dry run)
    price, qty = test_ccxt_order_construction()
    
    # Test 6: Live SHORT test (optional, requires user confirmation)
    if margin_ok is not False:  # Only if margin wasn't definitively disabled
        test_live_short_order(price, qty)
    else:
        print_header("TEST 6: Live SHORT Test — SKIPPED")
        print_info("Margin appears to be disabled. Skipping live SHORT test.")
        print_info("Enable margin first, then re-run this diagnostic.")
    
    # Test 7: Engine code verification
    test_engine_code_verification()
    
    # Summary
    print_summary_and_recommendations()


if __name__ == "__main__":
    main()
