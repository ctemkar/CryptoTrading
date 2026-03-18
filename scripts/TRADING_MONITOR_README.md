# Trading Monitoring System

This system monitors the trading dashboard, analyzes trades, and alerts on risk events.

## Files Created

1. **`trading_monitor.py`** - Main monitoring script
2. **`trading_monitoring.log`** - Detailed monitoring logs
3. **`critical_alerts.log`** - Critical alerts only
4. **`run_trading_monitor.sh`** - Bash scheduler script
5. **`com.chetantemkar.trading-monitor.plist`** - macOS launchd service file
6. **`trading-monitor.service`** - Linux systemd service file

## Features

### 1. Dashboard Monitoring
- Fetches real-time status from trading dashboard
- Monitors API health and responsiveness
- Tracks total trades and system status

### 2. Trade Analysis
- Analyzes completed trades from `completed_trades.json`
- Calculates buy/sell ratios and volumes
- Trades by model and symbol
- Recent trade activity tracking

### 3. Risk Management
- **Stop-Loss Monitoring**: Alerts when positions hit 3% stop-loss
- **Take-Profit Monitoring**: Alerts when positions hit 6% take-profit
- **Drawdown Analysis**: Critical alerts at 10% drawdown
- Position summary and net exposure

### 4. Alert System
- **Green Status**: No critical alerts
- **Yellow Status**: Take-profit triggers
- **Red Status**: Stop-loss triggers or critical drawdowns
- Detailed alert messages with recommended actions

## Usage

### Quick Test
```bash
python3 trading_monitor.py
```

### Continuous Monitoring (5-minute intervals)
```bash
python3 trading_monitor.py --continuous
```

### Using Bash Scheduler
```bash
./run_trading_monitor.sh
```

### macOS Service (launchd)
1. Copy plist to LaunchAgents:
   ```bash
   cp com.chetantemkar.trading-monitor.plist ~/Library/LaunchAgents/
   ```

2. Load and start the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.chetantemkar.trading-monitor.plist
   launchctl start com.chetantemkar.trading-monitor
   ```

3. Check status:
   ```bash
   launchctl list | grep trading-monitor
   ```

4. View logs:
   ```bash
   tail -f trading_monitor_service.log
   tail -f trading_monitor_service.error.log
   ```

### Linux Service (systemd)
1. Copy service file:
   ```bash
   sudo cp trading-monitor.service /etc/systemd/system/
   ```

2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable trading-monitor
   sudo systemctl start trading-monitor
   ```

3. Check status:
   ```bash
   sudo systemctl status trading-monitor
   ```

4. View logs:
   ```bash
   sudo journalctl -u trading-monitor -f
   ```

## Log Files

### `trading_monitoring.log`
- Detailed monitoring data every cycle
- Dashboard status and trade analysis
- Risk metrics and position summaries
- System health checks

### `critical_alerts.log`
- Only contains critical alerts
- Stop-loss and take-profit triggers
- Critical drawdown warnings
- Recommended actions

## Alert Examples

### Stop-Loss Trigger
```
[CRITICAL] STOP_LOSS_TRIGGERED
Symbol: BTC/USD
Message: Stop loss triggered for BTC/USD! Entry: $74500.00, Current: $72265.00, Drawdown: -3.00%
```

### Take-Profit Trigger
```
[MEDIUM] TAKE_PROFIT_TRIGGERED
Symbol: ETH/USD
Message: Take profit triggered for ETH/USD! Entry: $2340.00, Current: $2480.40, Profit: 6.00%
```

### Critical Drawdown
```
[CRITICAL] CRITICAL_DRAWDOWN
Symbol: SOL/USD
Message: Critical drawdown detected for SOL/USD! Drawdown: -12.50% (Threshold: 10.00%)
```

## Configuration

Risk parameters are configurable in `trading_monitor.py`:
```python
RISK_PARAMS = {
    "capital": 100.0,           # Initial capital
    "stop_loss_pct": 0.03,      # 3% stop loss
    "take_profit_pct": 0.06,    # 6% take profit
    "critical_drawdown_pct": 0.10,  # 10% critical drawdown
}
```

## Monitoring Interval

Default: 5 minutes (300 seconds)

To change:
- Script: Modify `interval_seconds` in `continuous_monitoring()` method
- launchd: Change `StartInterval` in plist file
- systemd: Modify `RestartSec` in service file

## Dependencies

- Python 3.6+
- requests library (included in most Python installations)
- Trading dashboard running on localhost:5001

## Troubleshooting

### Dashboard Not Responding
1. Check if dashboard is running: `curl http://localhost:5001/`
2. Check port in `.active_port` file
3. Verify API endpoints are accessible

### No Trades Found
1. Check `completed_trades.json` exists and has valid JSON
2. Verify trades have correct format with required fields

### Alerts Not Triggering
1. Check current prices in `calculate_risk_metrics()` method
2. Verify risk parameter thresholds
3. Check trade entry price calculations

## Integration with OpenClaw

This monitoring system can be integrated with OpenClaw for:
- Scheduled monitoring via cron events
- Alert notifications through Discord/Telegram
- Automated responses to critical events
- Performance reporting and analytics

## Next Steps

1. **Real-time Market Data**: Integrate with market data APIs for accurate price updates
2. **Multi-Asset Support**: Expand beyond BTC/ETH/SOL
3. **Advanced Analytics**: Add P&L tracking, Sharpe ratio, volatility metrics
4. **Notification Channels**: Add email, SMS, or messaging app alerts
5. **Web Dashboard**: Create a monitoring dashboard with charts and graphs
6. **Historical Analysis**: Add trend analysis and pattern recognition

## Support

For issues or feature requests:
1. Check logs in `trading_monitoring.log` and `critical_alerts.log`
2. Review system logs for service-related issues
3. Test individual components with the quick test command