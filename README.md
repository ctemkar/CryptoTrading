# CryptoTrading System

A comprehensive crypto trading system with LLM-powered strategies, real-time monitoring, and automated trading.

## Features

- **LLM Strategy Generation**: AI-powered trading strategies using OpenAI
- **Real-time Market Monitoring**: BTC/USD, ETH/USD, SOL/USD pairs
- **Automated Trading**: Buy/sell execution with risk management
- **Dashboard UI**: Web-based dashboard for monitoring and control
- **Health Checks**: Automated system monitoring and alerts

## Architecture

- `app.py` - Main Flask web application
- `gateway.py` - Trading gateway and API integration
- `trading_server.py` - Core trading logic
- `check_trading_v2.py` - Trading bot monitoring
- `market_analysis_current.py` - Market data analysis

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the dashboard:
```bash
python app.py
```

4. Start the trading bot:
```bash
python check_trading_v2.py
```

## Dashboard

Access the dashboard at: http://localhost:5080

## Backup Schedule

Automated hourly backups to this repository.