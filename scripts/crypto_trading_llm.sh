#!/bin/bash
CAPITAL=100.00
# TRADE_SIZE_USD_PER_ORDER=25.00 # Hardcoded value removed
STOP_LOSS_PCT=0.03
TAKE_PROFIT_PCT=0.06

EXEC_DIR=$(dirname "$0")
PYTHON_SCRIPT="${EXEC_DIR}/crypto_trading_llm_live.py"
VENV_ACTIVATE_SCRIPT="${EXEC_DIR}/venv/bin/activate"

# Load trade size from trading_config.json
CONFIG_FILE="${EXEC_DIR}/trading_config.json"
TRADE_SIZE_USD_PER_ORDER=$(jq -r '.trade_size_usd' "$CONFIG_FILE")

# Fallback to default if config or value is not found or invalid
if [ -z "$TRADE_SIZE_USD_PER_ORDER" ] || [ "$TRADE_SIZE_USD_PER_ORDER" == "null" ] || [[ ! "$TRADE_SIZE_USD_PER_ORDER" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Warning: Could not read valid TRADE_SIZE_USD_PER_ORDER from $CONFIG_FILE. Using default of $25.00."
    TRADE_SIZE_USD_PER_ORDER=25.00
fi

echo "🚀 Crypto Trading LLM Bot - REAL TRADING MODE (Calling Python Script)"
echo "========================================================================"
echo "Capital: \$${CAPITAL}"
echo "Trade Size: \$${TRADE_SIZE_USD_PER_ORDER} per trade"
echo "Risk: Stop loss ${STOP_LOSS_PCT}%, Take profit ${TAKE_PROFIT_PCT}%"
echo "Frequency: Currently set to run once per execution. For 30-min intervals, this script would be run by cron."
echo ""


PYTHON_CMD="python3"
if [ -f "$VENV_ACTIVATE_SCRIPT" ]; then
    source "$VENV_ACTIVATE_SCRIPT"
    if command -v python &> /dev/null; then
        PYTHON_CMD=$(command -v python)
        echo "Virtual environment activated. Using Python from: $PYTHON_CMD"
    else
        echo "⚠️ Virtual environment activated, but 'python' command not found. Relying on system python3."
    fi
else
    echo "⚠️ Virtual environment activate script not found at $VENV_ACTIVATE_SCRIPT. Relying on system python3."
fi

echo "Checking for ccxt library (using Python executable: $PYTHON_CMD)..."
if $PYTHON_CMD -c "import ccxt" >/dev/null 2>&1; then
    echo "✅ ccxt library is installed."
else
    echo "⚠️ ccxt library not found using $PYTHON_CMD."
    echo "Please ensure it is installed within the virtual environment:"
    echo "Activate venv: source $VENV_ACTIVATE_SCRIPT"
    echo "Then run: python3 -m pip install ccxt[gemini] numpy"
    exit 1
fi

echo "Executing Python live trading script using $PYTHON_CMD..."
$PYTHON_CMD "$PYTHON_SCRIPT"

echo ""
echo "✅ Crypto Trading LLM Bot execution finished."
