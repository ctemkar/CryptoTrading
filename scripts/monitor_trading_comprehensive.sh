#!/bin/bash

BASE_URL="http://localhost:5001"
TRADING_LOG="/Users/chetantemkar/.openclaw/workspace/app/trading_monitoring.log"
ALERT_LOG="/Users/chetantemkar/.openclaw/workspace/app/critical_alerts.log"
TIMESTAMP=$(date)

echo "--- $TIMESTAMP ---" >> "$TRADING_LOG"

# Fetch all relevant data
STATUS_RESPONSE=$(curl -s "$BASE_URL/api/status/all")
PROGRESS_RESPONSE=$(curl -s "$BASE_URL/api/trading/progress")
LOGS_RESPONSE=$(curl -s "$BASE_URL/api/trading/logs")

# Check if services are responding
if [ $? -ne 0 ] || [ -z "$STATUS_RESPONSE" ]; then
    echo "CRITICAL: Trading dashboard is not responding" >> "$ALERT_LOG"
    echo "Error: Dashboard not responding" >> "$TRADING_LOG"
    echo "Trading Dashboard Monitoring Summary:"
    echo "Timestamp: $TIMESTAMP"
    echo "Status: CRITICAL - Dashboard not responding"
    exit 1
fi

# Extract data
LAST_UPDATE=$(echo "$STATUS_RESPONSE" | jq -r '.last_update')
TRADING_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.trading')
TRADE_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '.trades | length')
ERROR_LOG=$(echo "$LOGS_RESPONSE" | jq -r '.logs')

# Log all data
echo "Status: $STATUS_RESPONSE" >> "$TRADING_LOG"
echo "Progress: $PROGRESS_RESPONSE" | jq '.' >> "$TRADING_LOG"
echo "Recent Logs:" >> "$TRADING_LOG"
echo "$ERROR_LOG" | tail -20 >> "$TRADING_LOG"

# Check for critical conditions
echo "--- $TIMESTAMP ---" >> "$ALERT_LOG"

# 1. Check trading status
if [ "$TRADING_STATUS" != "running" ]; then
    echo "CRITICAL: Trading status is '$TRADING_STATUS'" >> "$ALERT_LOG"
fi

# 2. Check for strategy errors in logs
ERROR_COUNT=$(echo "$ERROR_LOG" | grep -c "STRATEGY ERROR")
if [ $ERROR_COUNT -gt 0 ]; then
    echo "CRITICAL: $ERROR_COUNT strategy errors detected in recent logs" >> "$ALERT_LOG"
    # Extract most recent error
    RECENT_ERROR=$(echo "$ERROR_LOG" | grep "STRATEGY ERROR" | tail -1)
    echo "Most recent error: $RECENT_ERROR" >> "$ALERT_LOG"
fi

# 3. Check for API errors
API_ERROR_COUNT=$(echo "$ERROR_LOG" | grep -c "API ERROR")
if [ $API_ERROR_COUNT -gt 0 ]; then
    echo "WARNING: $API_ERROR_COUNT API errors detected" >> "$ALERT_LOG"
fi

# 4. Analyze trades
BUY_COUNT=0
SELL_COUNT=0
LATEST_SIDE=""
LATEST_STATUS=""

if [ $TRADE_COUNT -gt 0 ]; then
    LATEST_TRADE=$(echo "$PROGRESS_RESPONSE" | jq '.trades[0]')
    LATEST_SIDE=$(echo "$LATEST_TRADE" | jq -r '.side')
    LATEST_STATUS=$(echo "$LATEST_TRADE" | jq -r '.status')
    
    BUY_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '[.trades[] | select(.side == "buy")] | length')
    SELL_COUNT=$(echo "$PROGRESS_RESPONSE" | jq '[.trades[] | select(.side == "sell")] | length')
    
    # Check trade status
    if [ "$LATEST_STATUS" != "filled" ]; then
        echo "ALERT: Latest trade not filled (status: $LATEST_STATUS)" >> "$ALERT_LOG"
    fi
    
    # Check for trade bias
    TOTAL_TRADES=$((BUY_COUNT + SELL_COUNT))
    if [ $TOTAL_TRADES -gt 0 ]; then
        BUY_PERCENTAGE=$((BUY_COUNT * 100 / TOTAL_TRADES))
        if [ $BUY_PERCENTAGE -gt 80 ]; then
            echo "ALERT: Heavy buy bias ($BUY_PERCENTAGE% buys)" >> "$ALERT_LOG"
        elif [ $BUY_PERCENTAGE -lt 20 ]; then
            echo "ALERT: Heavy sell bias ($((100 - BUY_PERCENTAGE))% sells)" >> "$ALERT_LOG"
        fi
    fi
fi

# 5. Check for no recent successful trades (if we have logs)
LAST_SUCCESS=$(echo "$ERROR_LOG" | grep -i "success\|filled\|executed" | tail -1)
if [ -z "$LAST_SUCCESS" ] && [ $TRADE_COUNT -eq 0 ]; then
    echo "WARNING: No successful trades recorded" >> "$ALERT_LOG"
fi

# Generate comprehensive summary
SUMMARY="TRADING DASHBOARD MONITORING REPORT\n"
SUMMARY+="=====================================\n"
SUMMARY+="Timestamp: $TIMESTAMP\n\n"

SUMMARY+="SYSTEM STATUS\n"
SUMMARY+="-------------\n"
SUMMARY+="Trading Status: $TRADING_STATUS\n"
SUMMARY+="Last Update: $LAST_UPDATE\n\n"

SUMMARY+="TRADING ACTIVITY\n"
SUMMARY+="----------------\n"
SUMMARY+="Total Trades: $TRADE_COUNT\n"
if [ $TRADE_COUNT -gt 0 ]; then
    SUMMARY+="Buy Trades: $BUY_COUNT\n"
    SUMMARY+="Sell Trades: $SELL_COUNT\n"
    SUMMARY+="Latest Trade: $LATEST_SIDE ($LATEST_STATUS)\n"
fi
SUMMARY+="\n"

SUMMARY+="ERROR MONITORING\n"
SUMMARY+="----------------\n"
SUMMARY+="Strategy Errors (last hour): $ERROR_COUNT\n"
SUMMARY+="API Errors (last hour): $API_ERROR_COUNT\n"
if [ $ERROR_COUNT -gt 0 ]; then
    SUMMARY+="Most Recent Error: $(echo "$ERROR_LOG" | grep "STRATEGY ERROR" | tail -1 | cut -c1-60)...\n"
fi
SUMMARY+="\n"

SUMMARY+="ALERT STATUS\n"
SUMMARY+="------------\n"
# Get alerts from this run
RECENT_ALERTS=$(tail -10 "$ALERT_LOG" | grep -E "CRITICAL|WARNING|ALERT" | grep "$(date +"%Y-%m-%d")" || true)
if [ -n "$RECENT_ALERTS" ]; then
    echo "$RECENT_ALERTS" | while read -r alert; do
        SUMMARY+="• $alert\n"
    done
else
    SUMMARY+="✓ No new critical alerts\n"
fi

SUMMARY+="\nRECOMMENDED ACTIONS\n"
SUMMARY+="------------------\n"
if [ $ERROR_COUNT -gt 10 ]; then
    SUMMARY+="1. INVESTIGATE STRATEGY ERRORS: Continuous errors detected\n"
fi
if [ "$TRADING_STATUS" != "running" ]; then
    SUMMARY+="2. RESTART TRADING: System is not running\n"
fi
if [ $TRADE_COUNT -eq 0 ] && [ "$TRADING_STATUS" = "running" ]; then
    SUMMARY+="3. CHECK STRATEGY: Running but no trades executed\n"
fi
if [ -z "$RECENT_ALERTS" ] || [ $(echo "$RECENT_ALERTS" | grep -c "CRITICAL") -eq 0 ]; then
    SUMMARY+="✓ System operational\n"
fi

# Output summary
echo -e "$SUMMARY"

# Save summary to file
echo -e "$SUMMARY" > /Users/chetantemkar/.openclaw/workspace/app/trading_summary.txt

# Also append to monitoring log
echo -e "\nSummary generated at $TIMESTAMP" >> "$TRADING_LOG"