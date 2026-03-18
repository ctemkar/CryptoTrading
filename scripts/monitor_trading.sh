#!/bin/bash

# Get the actual port from the .active_port file
ACTIVE_PORT_FILE="/Users/chetantemkar/.openclaw/workspace/app/.active_port"
if [ -f "$ACTIVE_PORT_FILE" ]; then
    PORT=$(cat "$ACTIVE_PORT_FILE")
    URL="http://localhost:$PORT"
else
    # Fallback to provided URL or default
    URL="${1:-http://localhost:5001/}"
fi

TRADING_LOG="${2:-/Users/chetantemkar/.openclaw/workspace/app/trading_monitoring.log}"
ALERT_LOG="${3:-/Users/chetantemkar/.openclaw/workspace/app/critical_alerts.log}"

echo "--- $(date) ---" >> "$TRADING_LOG"

# Fetch data from the progress endpoint
PROGRESS_RESPONSE=$(curl -s "${URL}/api/trading/progress")

# Basic check if curl command was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch data from ${URL}/api/trading/progress" >> "$TRADING_LOG"
    echo "Error: Failed to fetch data from ${URL}/api/trading/progress" >> "$ALERT_LOG"
    exit 1
fi

# Fetch configuration
CONFIG_RESPONSE=$(curl -s "${URL}/api/trading/configure")

# Log status updates
echo "Status:" >> "$TRADING_LOG"
echo "$PROGRESS_RESPONSE" | jq '.status' >> "$TRADING_LOG"

echo "Recent Trades:" >> "$TRADING_LOG"
echo "$PROGRESS_RESPONSE" | jq '.trades[]' >> "$TRADING_LOG"

echo "Configuration:" >> "$TRADING_LOG"
echo "$CONFIG_RESPONSE" | jq '.config' >> "$TRADING_LOG"

# Extract and log trading information
TRADE_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '.trades | length')
LAST_TRADE_TIME="N/A"
if [ "$TRADE_COUNT" -gt 0 ]; then
    LAST_TRADE_TIME=$(echo "$PROGRESS_RESPONSE" | jq -r '.trades[0].time')
fi

# Detect and log alerts
echo "--- Alerts ---" >> "$ALERT_LOG"
if [ "$TRADE_COUNT" -gt 0 ]; then
    echo "Active Trades: $TRADE_COUNT" >> "$ALERT_LOG"
    echo "Last Trade Time: $LAST_TRADE_TIME" >> "$ALERT_LOG"
    
    # Check if last trade was more than 2 hours ago (potential issue)
    if [ "$LAST_TRADE_TIME" != "N/A" ]; then
        # Simple check - if time doesn't contain today's date, it might be old
        CURRENT_HOUR=$(date +%H | sed 's/^0//')  # Remove leading zero
        TRADE_HOUR=$(echo "$LAST_TRADE_TIME" | cut -d: -f1 | sed 's/^0//')  # Remove leading zero
        if [ ! -z "$TRADE_HOUR" ] && [ "$TRADE_HOUR" -lt $((CURRENT_HOUR - 2)) ]; then
            echo "Alert: Last trade was more than 2 hours ago at $LAST_TRADE_TIME" >> "$ALERT_LOG"
        fi
    fi
else
    echo "No trades recorded" >> "$ALERT_LOG"
fi

# Generate plain text summary
SUMMARY="Trading Dashboard Monitoring Summary:\n"
SUMMARY+="\n--- Logged Data ---\n"
SUMMARY+="Status: $(echo "$PROGRESS_RESPONSE" | jq '.status')\n"
SUMMARY+="Total Trades: $TRADE_COUNT\n"
SUMMARY+="Configuration: $(echo "$CONFIG_RESPONSE" | jq '.config')\n"

SUMMARY+="\n--- Critical Alerts ---\n"
if [ "$TRADE_COUNT" -eq 0 ]; then
    SUMMARY+="No trades recorded. Trading may not be active.\n"
elif [ "$LAST_TRADE_TIME" != "N/A" ]; then
    SUMMARY+="Last trade at: $LAST_TRADE_TIME\n"
    CURRENT_HOUR=$(date +%H | sed 's/^0//')  # Remove leading zero
    TRADE_HOUR=$(echo "$LAST_TRADE_TIME" | cut -d: -f1 | sed 's/^0//')  # Remove leading zero
    if [ ! -z "$TRADE_HOUR" ] && [ "$TRADE_HOUR" -lt $((CURRENT_HOUR - 2)) ]; then
        SUMMARY+="ALERT: Last trade was more than 2 hours ago!\n"
    fi
fi

echo -e "$SUMMARY"
echo -e "$SUMMARY" > /Users/chetantemkar/.openclaw/workspace/app/trading_summary.txt