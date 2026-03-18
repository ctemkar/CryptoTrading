import json
import requests
import time
from datetime import datetime

# Get current time
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S (Asia/Bangkok)')

# Get trading progress
try:
    progress = requests.get('http://localhost:59745/api/trading/progress', timeout=5).json()
except Exception as e:
    print(f"Error fetching trading progress: {e}")
    progress = {'status': 'ERROR', 'trades': []}

# Get configuration
try:
    config = requests.get('http://localhost:59745/api/trading/configure', timeout=5).json()
except Exception as e:
    print(f"Error fetching configuration: {e}")
    config = {'config': {'capital': 10000, 'stop_loss': 0.03, 'trade_size': 10}}

# Get current market prices (simulated for now - would need real API)
# Using approximate current prices
btc_price = 74344.98  # From previous log
eth_price = 2331.69
sol_price = 95.268

# Analyze positions
total_btc = 0
total_invested = 0
for trade in progress.get('trades', []):
    if trade.get('side') == 'buy' and trade.get('status') == 'filled':
        amount = trade.get('amount', 0)
        price = trade.get('price', 0)
        total_btc += amount
        total_invested += amount * price

current_value = total_btc * btc_price if total_btc > 0 else 0
pnl = current_value - total_invested
pnl_percent = (pnl / total_invested * 100) if total_invested > 0 else 0

# Check stop loss
stop_loss_threshold = config.get('config', {}).get('stop_loss', 0.03) * 100
stop_loss_triggered = pnl_percent <= -stop_loss_threshold

print('=== TRADING MONITORING CHECK: ' + current_time + ' ===')
print('Dashboard Gateway: http://localhost:5001/ (redirects to http://localhost:59745/)')
print('Active Port: 59745 (via gateway on 5001)')
print()
print('--- TRADING STATUS ---')
print(json.dumps(progress, indent=2))
print()
print('--- MARKET PRICES ---')
print(json.dumps({'BTC': btc_price, 'ETH': eth_price, 'SOL': sol_price, 'timestamp': current_time}, indent=2))
print()
print('--- POSITION ANALYSIS ---')
print('Total BTC: {:.8f}'.format(total_btc))
print('Total USD Invested: ${:.2f}'.format(total_invested))
if total_btc > 0:
    print('Average Buy Price: ${:.2f}'.format(total_invested/total_btc))
else:
    print('Average Buy Price: N/A')
print('Current BTC Price: ${:.2f}'.format(btc_price))
print('Current Position Value: ${:.2f}'.format(current_value))
print('P&L: ${:+.2f}'.format(pnl))
print('P&L %: {:.2f}%'.format(pnl_percent))
print('Stop loss triggered: {} (Loss is {:.2f}%, threshold is {:.2f}%)'.format(stop_loss_triggered, abs(pnl_percent), stop_loss_threshold))
print()
print('--- CRITICAL ALERTS CHECK ---')
if stop_loss_triggered:
    print('[CURRENT_TIME] 🚨 CRITICAL - STOP LOSS TRIGGERED! Loss: {:.2f}% exceeds threshold: {:.2f}%'.format(pnl_percent, stop_loss_threshold))
    print('[CURRENT_TIME] 🚨 CRITICAL - Manual intervention required - trading bot may not auto-sell')
    print('[CURRENT_TIME] 🚨 CRITICAL - Positions should be sold immediately')
else:
    print('[CURRENT_TIME] STATUS - Current loss: {:.2f}%, below {:.2f}% stop loss threshold'.format(abs(pnl_percent), stop_loss_threshold))
    if abs(pnl_percent) > stop_loss_threshold * 0.8:
        print('[CURRENT_TIME] ⚠️ WARNING - Loss approaching stop loss threshold ({:.2f}% vs {:.2f}%)'.format(abs(pnl_percent), stop_loss_threshold))
print()
print('=== END OF MONITORING CHECK ===')