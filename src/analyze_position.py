#!/usr/bin/env python3
import json
import math

# Current BTC price
btc_price = 74346

# Trade data from API
trades = [
    {'amount': 0.00013374340845611425, 'price': 74770.04},
    {'amount': 0.00013368983957219252, 'price': 74800.0},
    {'amount': 0.00013381716266667096, 'price': 74728.83},
    {'amount': 0.00013381716266667096, 'price': 74728.83}
]

# Calculate totals
total_btc = sum(t['amount'] for t in trades)
total_invested = sum(t['amount'] * t['price'] for t in trades)
current_value = total_btc * btc_price
pnl = current_value - total_invested
pnl_percent = (pnl / total_invested) * 100

# Stop loss threshold (3% from config)
stop_loss_threshold = -3.0

print('=== POSITION ANALYSIS ===')
print(f'Total BTC: {total_btc:.8f}')
print(f'Total USD Invested: ${total_invested:.2f}')
print(f'Average Buy Price: ${total_invested/total_btc:.2f}')
print(f'Current BTC Price: ${btc_price}')
print(f'Current Position Value: ${current_value:.2f}')
print(f'P&L: ${pnl:.2f}')
print(f'P&L %: {pnl_percent:.2f}%')
print(f'Stop Loss Threshold: {stop_loss_threshold}%')
print(f'Stop Loss Triggered: {pnl_percent <= stop_loss_threshold}')
print(f'Distance to Stop Loss: {abs(pnl_percent - stop_loss_threshold):.2f}%')

# Risk assessment
if pnl_percent <= stop_loss_threshold:
    print('🚨 CRITICAL: STOP LOSS TRIGGERED!')
elif pnl_percent <= stop_loss_threshold * 0.5:
    print('⚠️ WARNING: Approaching stop loss threshold')
elif pnl_percent <= stop_loss_threshold * 0.8:
    print('⚠️ CAUTION: Loss increasing, monitor closely')
else:
    print('✅ Within acceptable risk limits')