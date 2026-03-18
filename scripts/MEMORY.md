# MEMORY.md

This file serves as our persistent memory.

## Current Projects:

### Crypto Trading System
*   **Status:** Dashboard/API is running (port 61804) and trading bot has been restarted and is actively monitoring. Bot is scanning for buy opportunities every 5 minutes.
*   **Visuals Provided:** User shared an example of the app's UI.
*   **Current Challenge:** Port 5001 was in use when trying to start `app.py`, but was resolved. All hardcoded port references have been fixed to use dynamic port allocation.
*   **Recent Activity:** Progress monitor running every 10 minutes shows API port changes (62022 → 54213 → 61804). Bot restarted at 04:40 AM.
*   **Performance Analysis:** No trades table exists yet (database empty). Bot is actively scanning BTC/USD, ETH/USD, SOL/USD with LLM strategies but conditions not met.
*   **Next Steps/Proactive Areas:**
    *   Monitor bot for first trade execution.
    *   Analyze performance metrics once trades occur.
    *   Review and adjust risk management parameters (stop-loss, take-profit).
    *   Explore new trading strategies and backtest them.
    *   Enhance automated reporting.

## System Configuration & Operations:
*   Hourly Git backups are intended.
*   Attempted to read `MEMORY.md` but it was not found. Will create it now.

## User Instructions & Feedback:
*   Be more proactive. Identify and suggest improvements without being explicitly asked.
*   Prioritize self-improvement (memory, tool usage, project monitoring).
*   Follow instructions directly and avoid unnecessary assumptions.
*   Apologized for past instances of not following instructions precisely.
*   Resolved an issue with `app.py` not starting due to port conflict.
