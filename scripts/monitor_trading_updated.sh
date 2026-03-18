#!/bin/bash

BASE_URL="http://localhost:5001"
TRADING_LOG="/Users/chetantemkar/.openclaw/workspace/app/trading_monitoring.log"
ALERT_LOG="/Users/chetantemkar/.openclaw/workspace/app/critical_alerts.log"

echo "--- $(date) ---" >> "$TRADING_LOG"

# Fetch status data
STATUS_RESPONSE=$(curl -s "$BASE_URL/api/status/all")

# Fetch trading progress data
PROGRESS_RESPONSE=$(curl -s "$BASE_URL/api/trading/progress")

# Basic check if curl commands were successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch data from dashboard APIs" >> "$TRADING_LOG"
    echo "Error: Failed to fetch data from dashboard APIs" >> "$ALERT_LOG"
    exit 1
fi

# Log status updates
echo "Status Update:" >> "$TRADING_LOG"
echo "$STATUS_RESPONSE" | jq '.' >> "$TRADING_LOG"

# Log trading progress
echo "Trading Progress:" >> "$TRADING_LOG"
echo "$PROGRESS_RESPONSE" | jq '.' >> "$TRADING_LOG"

# Extract and analyze data
LAST_UPDATE=$(echo "$STATUS_RESPONSE" | jq -r '.last_update')
TRADING_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.trading')
TRADE_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '.trades | length')

# Check for critical conditions
echo "--- Alerts ---" >> "$ALERT_LOG"

# Check if trading is not running
if [ "$TRADING_STATUS" != "running" ]; then
    echo "CRITICAL: Trading status is '$TRADING_STATUS' (expected: 'running')" >> "$ALERT_LOG"
fi

# Check for recent trades (within last 5 minutes)
CURRENT_TIME=$(date -u +%s)
LAST_UPDATE_TIME=$(date -u -d "$LAST_UPDATE" +%s 2>/dev/null || echo "0")
TIME_DIFF=$((CURRENT_TIME - LAST_UPDATE_TIME))

if [ $TIME_DIFF -gt 300 ]; then  # 5 minutes = 300 seconds
    echo "WARNING: Last update was $TIME_DIFF seconds ago (more than 5 minutes)" >> "$ALERT_LOG"
fi

# Analyze trades for patterns
if [ $TRADE_COUNT -gt 0 ]; then
    # Get latest trade
    LATEST_TRADE=$(echo "$PROGRESS_RESPONSE" | jq '.trades[0]')
    LATEST_SIDE=$(echo "$LATEST_TRADE" | jq -r '.side')
    LATEST_STATUS=$(echo "$LATEST_TRADE" | jq -r '.status')
    
    if [ "$LATEST_STATUS" != "filled" ]; then
        echo "ALERT: Latest trade status is '$LATEST_STATUS' (not 'filled')" >> "$ALERT_LOG"
    fi
    
    # Count buy vs sell trades
    BUY_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '[.trades[] | select(.side == "buy")] | length')
    SELL_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '[.trades[] | select(.side == "sell")] | length')
    
    echo "Trade Analysis: $BUY_COUNT buy trades, $SELL_COUNT sell trades" >> "$TRADING_LOG"
fi

# Generate plain text summary
SUMMARY="Trading Dashboard Monitoring Summary:\n"
SUMMARY+="\n--- System Status ---\n"
SUMMARY+="Trading Status: $TRADING_STATUS\n"
SUMMARY+="Last Update: $LAST_UPDATE\n"
SUMMARY+="Time Since Last Update: $TIME_DIFF seconds\n"

SUMMARY+="\n--- Trading Activity ---\n"
SUMMARY+="Total Trades: $TRADE_COUNT\n"
if [ $TRADE_COUNT -gt 0 ]; then
    SUMMARY+="Buy Trades: $BUY_COUNT\n"
    SUMMARY+="Sell Trades: $SELL_COUNT\n"
    SUMMARY+="Latest Trade Side: $LATEST_SIDE\n"
    SUMMARY+="Latest Trade Status: $LATEST_STATUS\n"
fi

SUMMARY+="\n--- Critical Alerts ---\n"
ALERT_CONTENT=$(tail -20 "$ALERT_LOG" | grep -E "CRITICAL|WARNING|ALERT" || echo "No critical alerts in recent log entries.")
if [ -n "$ALERT_CONTENT" ] && [ "$ALERT_CONTENT" != "No critical alerts in recent log entries." ]; then
    SUMMARY+="$ALERT_CONTENT\n"
else
    SUMMARY+="No critical alerts detected.\n"
fi

echo -e "$SUMMARY"
echo -e "$SUMMARY" > /Users/chetantemkar/.openclaw/workspace/app/trading_summary.txt