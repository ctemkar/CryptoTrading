#!/bin/zsh
PORT_FILE="/Users/chetantemkar/.openclaw/workspace/app/.active_port"
LOG_FILE="/Users/chetantemkar/.openclaw/workspace/app/trading_bot_clean.log"

if [ -f "$LOG_FILE" ]; then
    tail -n 100 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

echo "--- Progress Monitor: $(date) ---"

if [ -f "$PORT_FILE" ]; then
    CURRENT_PORT=$(cat "$PORT_FILE")
    echo "Click to open Dashboard:"
    echo "http://127.0.0.1:$CURRENT_PORT"
    echo ""
    
    if ! curl -s "http://127.0.0.1:$CURRENT_PORT" > /dev/null; then
        echo "STATUS: [WARN] API is DOWN"
    else
        echo "STATUS: [OK] API is UP"
    fi
else
    echo "STATUS: [ERROR] Port file missing"
fi

if ! ps aux | grep -v grep | grep "crypto_trading_llm_live.py" > /dev/null; then
    echo "BOT: [WARN] NOT DETECTED"
else
    echo "BOT: [OK] RUNNING"
fi
