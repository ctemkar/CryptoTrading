# Gemini Margin Trading Setup Guide

## The Problem: "Insufficient Funds" on SHORT Orders

If you see errors like this in the engine logs:
```
❌ [EXECUTION ERROR] ethusd: gemini Failed to place sell order on symbol 'ETHUSD' 
   for price $2,134.55 and quantity 0.023377 ETH due to insufficient funds
```

This means the engine is trying to SHORT (sell crypto you don't own), and either:
1. **Your code is outdated** — doesn't have the `margin_order=True` fix
2. **Margin trading isn't enabled** on your Gemini account
3. **Both**

---

## Step 1: Pull the Latest Code

Make sure you have the latest version with the margin fix:

```bash
cd crypto-master-engine
git pull origin supabase-refactor-v2.1
```

Verify the fix is present:
```bash
grep "margin_order" master_engine.py
```

You should see: `order_params["margin_order"] = True`

---

## Step 2: Run the Diagnostic Tool

```bash
python check_gemini_account.py
```

This will check:
- ✅ API credentials are valid
- ✅ Account balances
- ✅ Whether margin trading is enabled
- ✅ What ccxt actually sends to Gemini
- ✅ (Optional) Live test of a tiny $5 SHORT order
- ✅ Engine code has the correct fixes

---

## Step 3: Check if Margin is Enabled on Gemini

### How to Check:
1. Log into [Gemini Exchange](https://exchange.gemini.com)
2. Go to **Account** → **Settings**
3. Look for **Margin Trading** section
4. Check if it says "Enabled" or "Eligible"

### How to Enable:
1. Go to [Gemini Settings](https://exchange.gemini.com/settings)
2. Navigate to **Margin Trading**
3. Accept the margin agreement
4. Complete any additional verification required

### Requirements for Gemini Margin:
- **Account type**: Individual (not institutional)
- **Verification**: Enhanced verification completed
- **Jurisdiction**: Available in eligible US states and some international regions
- **Not available**: Some US states restrict margin trading

---

## Step 4: If Margin Isn't Available — Use Close-Only Mode

If you **cannot** enable margin (wrong jurisdiction, account type, etc.), use **close-only mode**. This is a safe alternative that still profits from market signals:

### What Close-Only Mode Does:
| Signal | Normal Mode (margin) | Close-Only Mode |
|--------|---------------------|-----------------|
| BULLISH | Open LONG (buy) | Open LONG (buy) |
| BEARISH | Open SHORT (margin sell) | **Close existing LONG** |
| NEUTRAL | Hold / Close | Hold / Close |

### How to Enable Close-Only Mode:

Add to your `.env` file:
```bash
SHORT_MODE=close_only
```

Or run the engine with:
```bash
SHORT_MODE=close_only python master_engine.py
```

### How Close-Only Mode Profits:
- Engine buys when BULLISH (price going up)
- Engine sells when BEARISH (locks in profit or cuts losses)
- No margin required — all trades are spot (buy/sell crypto you own)
- You won't profit from downward moves, but you won't lose either

---

## Step 5: Enable Verbose Logging for Debugging

If orders are still failing, enable verbose logging to see exactly what's being sent:

Add to your `.env` file:
```bash
VERBOSE_ORDERS=true
```

This will log:
- The exact parameters sent to `create_order()`
- Whether `margin_order=True` is in the params
- The exact Gemini API response

---

## Quick Reference: .env Settings

```bash
# Required
GEMINI_API_KEY=your_key_here
GEMINI_API_SECRET=your_secret_here

# Optional: Supabase (for persistent state)
SUPABASE_URL=your_url
SUPABASE_KEY=your_key

# SHORT handling (default: margin)
# SHORT_MODE=margin       # Use margin for shorts (requires Gemini margin)
# SHORT_MODE=close_only   # Close longs on bearish signals (no margin needed)

# Debug logging (default: false)
# VERBOSE_ORDERS=true     # Log exact API requests/responses

# Trading parameters
# TRADE_SIZE_USD=50       # Max USD per trade
# BEARISH_THRESHOLD=58    # Confidence % needed for bearish action
# BULLISH_THRESHOLD=58    # Confidence % needed for bullish action
```

---

## Technical Details: Why the Old Code Failed

### The Bug (fixed in v2.2):
The old code used `params={'type': 'limit'}` for margin orders. But ccxt's `gemini.create_order()` **strips** the `type` key from params internally before sending to the Gemini API. So the order was sent as a regular spot order.

### The Fix:
The correct parameter is `params={'margin_order': True}`. This passes through ccxt to the Gemini API and tells Gemini to treat the order as a margin order (allowing short-selling borrowed assets).

### Code Location:
In `master_engine.py`, the `place_order()` function:
```python
order_params = {}
if use_margin:
    order_params["margin_order"] = True

order = exchange.create_order(
    symbol=symbol,
    type="limit",
    side=side,
    amount=qty,
    price=price,
    params=order_params,  # margin_order=True passed to Gemini API
)
```

---

## Still Having Issues?

1. Run `python check_gemini_account.py` and share the output
2. Check the engine logs for `[VERBOSE]` entries (with `VERBOSE_ORDERS=true`)
3. Verify your Gemini API key has **trading permissions** (not just read-only)
4. Make sure you have enough USD balance ($70+ recommended: $20 reserve + $50 trade size)
