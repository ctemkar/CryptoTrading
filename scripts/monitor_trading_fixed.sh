#!/bin/bash

PORT="57260"
URL="http://localhost:$PORT"
TRADING_LOG="/Users/chetantemkar/.openclaw/workspace/app/trading_monitoring.log"
ALERT_LOG="/Users/chetantemkar/.openclaw/workspace/app/critical_alerts.log"

echo "--- $(date) ---" >> "$TRADING_LOG"

# Fetch trading progress data
PROGRESS_RESPONSE=$(curl -s "$URL/api/trading/progress")
CONFIG_RESPONSE=$(curl -s "$URL/api/trading/configure")

# Check if curl commands were successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch data from dashboard" >> "$TRADING_LOG"
    echo "Error: Failed to fetch data from dashboard" >> "$ALERT_LOG"
    exit 1
fi

# Log status updates
echo "Trading Status:" >> "$TRADING_LOG"
echo "$PROGRESS_RESPONSE" | jq '.status' >> "$TRADING_LOG"

echo "Trading Configuration:" >> "$TRADING_LOG"
echo "$CONFIG_RESPONSE" | jq '.config' >> "$TRADING_LOG"

# Check for completed trades
TRADE_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '.trades | length')
echo "Completed Trades: $TRADE_COUNT" >> "$TRADING_LOG"

# Check trading logs file directly
TRADING_LOGS_FILE="/Users/chetantemkar/.openclaw/workspace/app/trading_bot_clean.log"
if [ -f "$TRADING_LOGS_FILE" ]; then
    echo "Recent Trading Logs:" >> "$TRADING_LOG"
    tail -10 "$TRADING_LOGS_FILE" >> "$TRADING_LOG"
    
    # Check for critical alerts in logs
    echo "--- Alerts ---" >> "$ALERT_LOG"
    if grep -i "stop-loss\|take-profit\|critical\|error\|failed" "$TRADING_LOGS_FILE" | tail -5; then
        grep -i "stop-loss\|take-profit\|critical\|error\|failed" "$TRADING_LOGS_FILE" | tail -5 >> "$ALERT_LOG"
    fi
else
    echo "No trading logs file found" >> "$TRADING_LOG"
fi

# Generate plain text summary
SUMMARY="Trading Dashboard Monitoring Summary:\n"
SUMMARY+="\n--- Dashboard Status ---\n"
SUMMARY+="Dashboard URL: $URL\n"
SUMMARY+="Trading Status: $(echo "$PROGRESS_RESPONSE" | jq -r '.status')\n"
SUMMARY+="Completed Trades: $TRADE_COUNT\n"

SUMMARY+="\n--- Configuration ---\n"
CAPITAL=$(echo "$CONFIG_RESPONSE" | jq -r '.config.capital')
STOP_LOSS=$(echo "$CONFIG_RESPONSE" | jq -r '.config.stop_loss')
TRADE_SIZE=$(echo "$CONFIG_RESPONSE" | jq -r '.config.trade_size')
SUMMARY+="Capital: \$$CAPITAL\n"
SUMMARY+="Stop Loss: ${STOP_LOSS}%\n"
SUMMARY+="Trade Size: \$$TRADE_SIZE\n"

SUMMARY+="\n--- Critical Alerts ---\n"
if [ -f "$ALERT_LOG" ] && [ -s "$ALERT_LOG" ]; then
    ALERT_COUNT=$(grep -c "stop-loss\|take-profit\|critical\|error\|failed" "$ALERT_LOG" 2>/dev/null || echo "0")
    if [ "$ALERT_COUNT" -gt 0 ]; then
        SUMMARY+="Found $ALERT_COUNT alert(s) in logs\n"
        SUMMARY+="Latest alerts:\n"
        tail -3 "$ALERT_LOG" | while read line; do
            SUMMARY+="  - $line\n"
        done
    else
        SUMMARY+="No critical alerts detected.\n"
    fi
else
    SUMMARY+="No critical alerts detected.\n"
fi

echo -e "$SUMMARY"
echo -e "$SUMMARY" > /Users/chetantemkar/.openclaw/workspace/app/trading_summary.txt