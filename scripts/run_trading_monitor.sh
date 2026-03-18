#!/bin/bash
# Trading Monitor Scheduler Script
# Runs the trading monitor at specified intervals

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/trading_monitor.py"
LOG_FILE="$SCRIPT_DIR/trading_monitor_scheduler.log"

# Configuration
INTERVAL_SECONDS=300  # 5 minutes
MAX_RUNS=1000         # Maximum number of runs (for safety)

echo "Starting Trading Monitor Scheduler at $(date)" >> "$LOG_FILE"
echo "Interval: ${INTERVAL_SECONDS}s" >> "$LOG_FILE"
echo "Max Runs: $MAX_RUNS" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"

for ((run=1; run<=MAX_RUNS; run++)); do
    echo "[$(date)] Run $run/$MAX_RUNS - Starting monitoring cycle..." >> "$LOG_FILE"
    
    # Run the monitoring script
    python3 "$MONITOR_SCRIPT" >> "$LOG_FILE" 2>&1
    
    # Check exit status
    if [ $? -eq 0 ]; then
        echo "[$(date)] Run $run completed successfully" >> "$LOG_FILE"
    else
        echo "[$(date)] ERROR: Run $run failed with exit code $?" >> "$LOG_FILE"
        # Wait a bit longer before retry
        sleep 60
    fi
    
    # Log interval information
    if [ $run -lt $MAX_RUNS ]; then
        echo "[$(date)] Waiting ${INTERVAL_SECONDS}s before next run..." >> "$LOG_FILE"
        echo "---" >> "$LOG_FILE"
        sleep $INTERVAL_SECONDS
    fi
done

echo "[$(date)] Maximum runs reached. Scheduler stopping." >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"