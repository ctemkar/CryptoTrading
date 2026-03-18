#!/usr/bin/env python3
import json
import requests
from datetime import datetime

def get_market_data():
    """Fetch current market data for BTC and ETH"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        btc_price = data["bitcoin"]["usd"]
        btc_change = data["bitcoin"]["usd_24h_change"]
        
        eth_price = data["ethereum"]["usd"]
        eth_change = data["ethereum"]["usd_24h_change"]
        
        return {
            "btc": {"price": btc_price, "change": btc_change},
            "eth": {"price": eth_price, "change": eth_change}
        }
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return None

def analyze_market_sentiment(market_data):
    """Analyze market sentiment based on price changes"""
    if not market_data:
        return "NEUTRAL", 50
    
    btc_change = market_data["btc"]["change"]
    eth_change = market_data["eth"]["change"]
    
    # Conservative sentiment analysis
    avg_change = (btc_change + eth_change) / 2
    
    if avg_change > 2.0:
        sentiment = "BULLISH"
        confidence = min(70 + (avg_change - 2) * 5, 85)
    elif avg_change < -2.0:
        sentiment = "BEARISH"
        confidence = min(70 + abs(avg_change - 2) * 5, 85)
    else:
        sentiment = "NEUTRAL"
        confidence = 50
    
    return sentiment, confidence

def calculate_support_resistance(price, change):
    """Calculate approximate support and resistance levels"""
    if change > 0:
        # In uptrend
        support1 = price * 0.98
        support2 = price * 0.96
        resistance1 = price * 1.02
        resistance2 = price * 1.04
    elif change < 0:
        # In downtrend
        support1 = price * 0.96
        support2 = price * 0.94
        resistance1 = price * 1.01
        resistance2 = price * 1.03
    else:
        # Sideways
        support1 = price * 0.99
        support2 = price * 0.98
        resistance1 = price * 1.01
        resistance2 = price * 1.02
    
    return {
        "support": [support1, support2],
        "resistance": [resistance1, resistance2]
    }

def main():
    print("CONSERVATIVE CRYPTO TRADING ANALYSIS")
    print("=" * 50)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get market data
    market_data = get_market_data()
    if not market_data:
        print("ERROR: Could not fetch market data")
        return
    
    btc_price = market_data["btc"]["price"]
    btc_change = market_data["btc"]["change"]
    eth_price = market_data["eth"]["price"]
    eth_change = market_data["eth"]["change"]
    
    print("CURRENT MARKET PRICES:")
    print(f"BTC/USD: ${btc_price:,.2f} ({btc_change:+.2f}%)")
    print(f"ETH/USD: ${eth_price:,.2f} ({eth_change:+.2f}%)")
    print()
    
    # Analyze sentiment
    sentiment, confidence = analyze_market_sentiment(market_data)
    print("MARKET SENTIMENT ANALYSIS:")
    print(f"Sentiment: {sentiment}")
    print(f"Confidence: {confidence:.0f}%")
    print()
    
    # Calculate support/resistance
    btc_levels = calculate_support_resistance(btc_price, btc_change)
    eth_levels = calculate_support_resistance(eth_price, eth_change)
    
    print("TECHNICAL LEVELS:")
    print("BTC Support: ${:,.0f}, ${:,.0f}".format(*btc_levels["support"]))
    print("BTC Resistance: ${:,.0f}, ${:,.0f}".format(*btc_levels["resistance"]))
    print("ETH Support: ${:,.0f}, ${:,.0f}".format(*eth_levels["support"]))
    print("ETH Resistance: ${:,.0f}, ${:,.0f}".format(*eth_levels["resistance"]))
    print()
    
    # Trading decision
    print("TRADING DECISION:")
    if confidence < 60:
        print("❌ NO TRADE RECOMMENDED")
        print(f"Reason: Confidence level ({confidence:.0f}%) below 60% threshold")
        print("Conservative strategy requires high confidence for trade execution")
    else:
        if sentiment == "BULLISH":
            print("✅ BUY RECOMMENDED")
            print("Reason: Bullish sentiment with sufficient confidence")
        elif sentiment == "BEARISH":
            print("✅ SELL/SHORT RECOMMENDED")
            print("Reason: Bearish sentiment with sufficient confidence")
        else:
            print("❌ NO TRADE RECOMMENDED")
            print("Reason: Neutral market conditions")
    
    print()
    print("RISK PARAMETERS:")
    print("• Capital: $1,000")
    print("• Stop-Loss: 5%")
    print("• Take-Profit: 10%")
    print("• Max Trades/Day: 2")
    print("• Max Position Size: $200 per trade")

if __name__ == "__main__":
    main()