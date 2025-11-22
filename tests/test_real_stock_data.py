#!/usr/bin/env python3
"""
Test Stock Swarm with REAL DATA
================================
This demonstrates the stock swarm working with actual market data.

To use real data, you need a free Alpha Vantage API key:
1. Get one at: https://www.alphavantage.co/support/#api-key
2. Set it: export ALPHA_VANTAGE_API_KEY=your_key_here
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from kg.models.graph_manager import KnowledgeGraphManager
from stock_analysis_swarm.agents.orchestrator import StockOrchestratorAgent
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

async def main():
    print("\n" + "=" * 80)
    print("🚀 STOCK SWARM WITH REAL DATA DEMONSTRATION")
    print("=" * 80)
    
    # Check for API key
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if api_key:
        print(f"✅ Alpha Vantage API Key Found: {api_key[:8]}...")
        print("   Using REAL MARKET DATA")
    else:
        print("⚠️  No Alpha Vantage API Key Found")
        print("   To use real data:")
        print("   1. Get a free key at: https://www.alphavantage.co/support/#api-key")
        print("   2. Set it: export ALPHA_VANTAGE_API_KEY=your_key_here")
        print("   ")
        print("   Continuing with MOCK DATA...")
    
    print("\n" + "-" * 80)
    
    # Initialize components
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    
    orchestrator = StockOrchestratorAgent(
        agent_id="real-data-orchestrator",
        knowledge_graph=kg
    )
    await orchestrator.initialize()
    
    # Test with real stocks
    stocks_to_test = ["AAPL", "MSFT", "GOOGL"]
    
    print("\n📊 ANALYZING STOCKS WITH REAL OR MOCK DATA:")
    print("-" * 80)
    
    for ticker in stocks_to_test:
        print(f"\nAnalyzing {ticker}...")
        
        try:
            result = await orchestrator.analyze_stock(ticker, "quick")
            
            # Check if we got real or mock data
            research = result.get("research", {})
            fundamental = research.get("fundamental", {})
            technical = research.get("technical", {})
            sentiment = research.get("sentiment", {})
            
            is_real_fundamental = fundamental.get("data_source") == "REAL_ALPHA_VANTAGE"
            is_real_technical = technical.get("data_source") == "REAL_ALPHA_VANTAGE"
            is_real_sentiment = sentiment.get("data_source") == "REAL_ALPHA_VANTAGE"
            
            print(f"\n📈 {ticker} Analysis Results:")
            print(f"   Overall Score: {result.get('opportunity_score', 0):.2f}")
            print(f"   Risk Level: {result.get('risk_assessment', {}).get('risk_level', 'N/A')}")
            print(f"   Recommendation: {result.get('recommendation', 'N/A')}")
            
            print(f"\n   📊 Fundamental Analysis ({fundamental.get('data_source', 'UNKNOWN')}):")
            if is_real_fundamental:
                print(f"      P/E Ratio: {fundamental.get('pe_ratio', 'N/A')} (REAL)")
                print(f"      EPS: ${fundamental.get('eps', 'N/A')} (REAL)")
                print(f"      Market Cap: ${fundamental.get('market_cap', 0):,} (REAL)")
                print(f"      Profit Margin: {fundamental.get('profit_margin', 0)*100:.1f}% (REAL)")
                print(f"      Analyst Target: ${fundamental.get('analyst_target', 'N/A')} (REAL)")
            else:
                print(f"      P/E Ratio: {fundamental.get('pe_ratio', 'N/A')} (MOCK)")
                print(f"      Score: {fundamental.get('score', 'N/A')} (MOCK)")
            
            print(f"\n   📈 Technical Analysis ({technical.get('data_source', 'UNKNOWN')}):")
            if is_real_technical:
                print(f"      Current Price: ${technical.get('current_price', 'N/A')} (REAL)")
                print(f"      RSI: {technical.get('rsi', 'N/A')} (REAL)")
                print(f"      50-Day MA: ${technical.get('sma_50', 'N/A')} (REAL)")
                print(f"      200-Day MA: ${technical.get('sma_200', 'N/A')} (REAL)")
                print(f"      Trend: {technical.get('trend', 'N/A')} (REAL)")
            else:
                print(f"      RSI: {technical.get('rsi', 'N/A')} (MOCK)")
                print(f"      Trend: {technical.get('trend', 'N/A')} (MOCK)")
            
            print(f"\n   💭 Sentiment Analysis ({sentiment.get('data_source', 'UNKNOWN')}):")
            if is_real_sentiment:
                print(f"      News Sentiment: {sentiment.get('news_sentiment', 'N/A')} (REAL)")
                print(f"      Sentiment Label: {sentiment.get('sentiment_label', 'N/A')} (REAL)")
                print(f"      Articles Analyzed: {sentiment.get('article_count', 0)} (REAL)")
                if sentiment.get('recent_articles'):
                    print(f"      Recent Headlines:")
                    for article in sentiment.get('recent_articles', [])[:2]:
                        print(f"        • {article.get('title', 'N/A')[:60]}...")
            else:
                print(f"      Sentiment Score: {sentiment.get('news_sentiment', 'N/A')} (MOCK)")
            
            # Show signals
            if result.get('signals'):
                print(f"\n   🚦 Trading Signals:")
                for signal in result['signals']:
                    data_type = "(REAL)" if any([is_real_fundamental, is_real_technical, is_real_sentiment]) else "(MOCK)"
                    print(f"      • {signal['type'].upper()}: {signal['source']} {data_type}")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {ticker}: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📝 SUMMARY")
    print("=" * 80)
    
    if api_key:
        print("✅ Successfully demonstrated stock analysis with REAL market data")
        print("   • Real P/E ratios, EPS, and market cap from Alpha Vantage")
        print("   • Real technical indicators (RSI, moving averages)")
        print("   • Real news sentiment analysis")
        print("   • Recommendations based on actual market conditions")
    else:
        print("⚠️  Demonstrated with MOCK data (no API key provided)")
        print("   To see real market data:")
        print("   1. Get a free API key from Alpha Vantage")
        print("   2. Export it as ALPHA_VANTAGE_API_KEY")
        print("   3. Run this script again")
    
    await kg.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
