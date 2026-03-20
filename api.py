#!/usr/bin/env python3
"""
Crypto Master Dashboard API  (Flask)
=====================================
Serves the dashboard UI at localhost:5001 and provides JSON endpoints
for the frontend to poll engine state.

Endpoints:
  GET /                  – Dashboard HTML
  GET /api/status        – Engine status, balance, positions, analysis, logs
  GET /api/positions     – Active positions from Supabase
  GET /api/trades        – Trade history from Supabase (with P&L)
  POST /api/engine/start – Start engine cycle manually
"""

import os
import json
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Import engine module for shared state
import master_engine as engine

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
CORS(app)

# ---------------------------------------------------------------------------
# Dashboard route
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    """Return full dashboard state including analysis with SMA values."""
    balance = engine.LATEST_BALANCE or 0
    positions = engine.sb_get_positions()
    analysis = engine.LATEST_ANALYSIS or {}
    logs = list(engine.LOG_BUFFER)

    # Enrich analysis with action signals for the dashboard
    enriched = {}
    for tag, a in analysis.items():
        enriched[tag] = {
            **a,
            "action": engine.determine_action(a.get("sentiment", "NEUTRAL"), a.get("confidence", 50)),
        }

    return jsonify({
        "balance": balance,
        "positions": positions,
        "analysis": enriched,
        "logs": logs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/positions")
def api_positions():
    """Return active positions with current price for unrealized P&L calc."""
    positions = engine.sb_get_positions()
    analysis = engine.LATEST_ANALYSIS or {}

    enriched = []
    for p in positions:
        current_price = 0
        if p["symbol"] in analysis:
            current_price = analysis[p["symbol"]].get("price", 0)

        entry = float(p.get("entry_price", 0))
        qty = float(p.get("qty", 0))
        side = p.get("side", "buy")

        if current_price > 0 and entry > 0:
            if side == "buy":
                unrealized_pnl = (current_price - entry) * qty
            else:
                unrealized_pnl = (entry - current_price) * qty
        else:
            unrealized_pnl = 0

        enriched.append({
            **p,
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2),
        })

    return jsonify({"positions": enriched})


@app.route("/api/trades")
def api_trades():
    """Fetch trade history from Supabase with full details."""
    if engine.supabase is None:
        return jsonify({"trades": [], "error": "Supabase not connected"})
    try:
        resp = (engine.supabase.table("trades")
                .select("*")
                .order("executed_at", desc=True)
                .limit(100)
                .execute())
        trades = resp.data or []

        # Calculate summary stats
        closed = [t for t in trades if t.get("action") == "close"]
        total_pnl = sum(float(t.get("pnl", 0)) for t in closed)
        wins = sum(1 for t in closed if float(t.get("pnl", 0)) > 0)
        losses = sum(1 for t in closed if float(t.get("pnl", 0)) < 0)
        buys = sum(1 for t in trades if t.get("side") == "buy")
        sells = sum(1 for t in trades if t.get("side") == "sell")

        return jsonify({
            "trades": trades,
            "summary": {
                "total_trades": len(trades),
                "closed_trades": len(closed),
                "total_pnl": round(total_pnl, 2),
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / len(closed) * 100, 1) if closed else 0,
                "buys": buys,
                "sells": sells,
            }
        })
    except Exception as e:
        return jsonify({"trades": [], "error": str(e)})


@app.route("/api/engine/start", methods=["POST"])
def api_engine_start():
    """Trigger an immediate analysis cycle in background."""
    t = threading.Thread(target=engine.run_cycle, daemon=True)
    t.start()
    return jsonify({"status": "cycle_started"})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def start_api(port=5001):
    """Start the Flask dashboard server."""
    print(f"🌐 Dashboard running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Initialize engine clients
    try:
        engine.init_exchange()
    except Exception as e:
        print(f"⚠️  Exchange init skipped: {e}")
    try:
        engine.init_supabase()
    except Exception as e:
        print(f"⚠️  Supabase init skipped: {e}")

    # Start engine in background thread
    engine_thread = threading.Thread(target=engine.start_engine, daemon=True)
    engine_thread.start()

    # Start API server (blocks)
    start_api()
