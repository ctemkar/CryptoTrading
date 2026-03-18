#!/usr/bin/env python3
"""
Conservative Crypto Trading Server
Runs on port 5001 and provides API endpoints for trading system
"""

from flask import Flask, jsonify, request
import subprocess
import json
import os
import time
from datetime import datetime
from threading import Thread
import schedule

app = Flask(__name__)
BASE_DIR = "/Users/chetantemkar/.openclaw/workspace/app"

# Files
TRADES_LOG = os.path.join(BASE_DIR, "completed_trades.json")
STRATEGY_FILE = os.path.join(BASE_DIR, "llm_strategies.json")
TRADING_HISTORY = os.path.join(BASE_DIR, "trading_history.json")
SUMMARY_FILE = os.path.join(BASE_DIR, "trading_summary.txt")

def run_trading_analysis():
    """Run the conservative trading analysis"""
    print(f"[{datetime.now()}] Running trading analysis...")
    try:
        result = subprocess.run(
            ["python3", os.path.join(BASE_DIR, "conservative_crypto_trading.py")],
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )
        
        # Create summary
        with open(SUMMARY_FILE, 'w') as f:
            f.write(f"TRADING ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\nERRORS:\n")
                f.write(result.stderr)
        
        print(f"[{datetime.now()}] Analysis complete")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Analysis failed: {e}")
        return False

def schedule_analysis():
    """Schedule hourly analysis"""
    schedule.every().hour.do(run_trading_analysis)
    
    # Run initial analysis
    run_trading_analysis()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

@app.route('/')
def index():
    """Home page with trading system info"""
    return """
    <html>
    <head><title>Conservative Crypto Trading System</title></head>
    <body>
        <h1>Conservative Crypto Trading System</h1>
        <p>Real trading with $1,000 capital on Gemini</p>
        
        <h2>Endpoints:</h2>
        <ul>
            <li><a href="/status">/status</a> - System status</li>
            <li><a href="/analysis">/analysis</a> - Run analysis now</li>
            <li><a href="/trades">/trades</a> - Recent trades</li>
            <li><a href="/strategy">/strategy</a> - Current strategy</li>
            <li><a href="/summary">/summary</a> - Trading summary</li>
        </ul>
        
        <h2>Configuration:</h2>
        <ul>
            <li>Capital: $1,000</li>
            <li>Stop-loss: 5%</li>
            <li>Take-profit: 10%</li>
            <li>Max trades/day: 2</li>
            <li>Pairs: BTC/USD, ETH/USD</li>
        </ul>
    </body>
    </html>
    """

@app.route('/status')
def get_status():
    """Get system status"""
    status = {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "port": 5001,
        "analysis_scheduled": "hourly",
        "capital": 1000.0,
        "risk_parameters": {
            "stop_loss": 0.05,
            "take_profit": 0.10,
            "max_trades_per_day": 2
        },
        "trading_pairs": ["BTC/USD", "ETH/USD"]
    }
    
    # Check if analysis is running
    try:
        with open(SUMMARY_FILE, 'r') as f:
            last_update = os.path.getmtime(SUMMARY_FILE)
            status["last_analysis"] = datetime.fromtimestamp(last_update).isoformat()
    except:
        status["last_analysis"] = None
    
    return jsonify(status)

@app.route('/analysis', methods=['GET', 'POST'])
def run_analysis():
    """Run trading analysis now"""
    if request.method == 'POST':
        # Run analysis
        success = run_trading_analysis()
        return jsonify({
            "success": success,
            "message": "Analysis completed" if success else "Analysis failed",
            "timestamp": datetime.now().isoformat()
        })
    else:
        # Show analysis form
        return """
        <html>
        <head><title>Run Trading Analysis</title></head>
        <body>
            <h1>Run Trading Analysis</h1>
            <form method="POST">
                <button type="submit">Run Analysis Now</button>
            </form>
            <p><a href="/">Back to home</a></p>
        </body>
        </html>
        """

@app.route('/trades')
def get_trades():
    """Get recent trades"""
    try:
        with open(TRADES_LOG, 'r') as f:
            trades = json.load(f)
        return jsonify({
            "trades": trades,
            "count": len(trades),
            "timestamp": datetime.now().isoformat()
        })
    except:
        return jsonify({
            "trades": [],
            "count": 0,
            "timestamp": datetime.now().isoformat(),
            "error": "No trades found"
        })

@app.route('/strategy')
def get_strategy():
    """Get current strategy"""
    try:
        with open(STRATEGY_FILE, 'r') as f:
            strategy = json.load(f)
        return jsonify(strategy)
    except:
        return jsonify({
            "error": "No strategy file found",
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/llm/strategies')
def get_llm_strategies():
    """API endpoint for LLM strategies (compatibility)"""
    try:
        with open(STRATEGY_FILE, 'r') as f:
            strategy = json.load(f)
        return jsonify([strategy])  # Return as array for compatibility
    except:
        return jsonify([])  # Return empty array if no strategy

@app.route('/summary')
def get_summary():
    """Get trading summary"""
    try:
        with open(SUMMARY_FILE, 'r') as f:
            summary = f.read()
        return f"<pre>{summary}</pre>"
    except:
        return "No summary available"

if __name__ == '__main__':
    # Start scheduling thread
    scheduler_thread = Thread(target=schedule_analysis, daemon=True)
    scheduler_thread.start()
    
    # Start Flask server
    print(f"Starting Conservative Crypto Trading Server on port 5001...")
    print(f"Capital: $1,000 | Stop-loss: 5% | Take-profit: 10%")
    print(f"Max trades/day: 2 | Pairs: BTC/USD, ETH/USD")
    print(f"Server running at http://localhost:5001")
    
    app.run(host='0.0.0.0', port=5001, debug=False)