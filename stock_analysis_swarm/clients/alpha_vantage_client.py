"""
Alpha Vantage API Client for Real Stock Data
=============================================
This provides REAL market data, not mock data.
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from loguru import logger
import json
from datetime import datetime, timedelta

class AlphaVantageClient:
    """Client for fetching real stock data from Alpha Vantage API"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Alpha Vantage client.
        
        Args:
            api_key: Alpha Vantage API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.session = None
        self._cache = {}  # Simple cache to avoid hitting rate limits
        self._last_request_time = None
        
        if not self.api_key:
            logger.warning("No Alpha Vantage API key found. Get one free at https://www.alphavantage.co/support/#api-key")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make a request to Alpha Vantage API.
        
        Args:
            params: Query parameters
            
        Returns:
            API response as dictionary
        """
        if not self.api_key:
            logger.error("No API key available")
            return {}
        
        # Rate limiting (5 calls per minute for free tier)
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < 12:  # 5 calls per minute = 12 seconds between calls
                await asyncio.sleep(12 - elapsed)
        
        params["apikey"] = self.api_key
        
        # Check cache
        cache_key = json.dumps(params, sort_keys=True)
        if cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < 300:  # 5 minute cache
                logger.debug(f"Using cached data for {params.get('symbol', 'unknown')}")
                return cached_data
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(self.BASE_URL, params=params) as response:
                self._last_request_time = datetime.now()
                
                if response.status != 200:
                    logger.error(f"API request failed with status {response.status}")
                    return {}
                
                data = await response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    logger.error(f"API error: {data['Error Message']}")
                    return {}
                
                if "Note" in data:  # Rate limit message
                    logger.warning(f"API note: {data['Note']}")
                    return {}
                
                # Cache successful response
                self._cache[cache_key] = (data, datetime.now())
                
                return data
                
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return {}
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Quote data including price, volume, change
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        data = await self._make_request(params)
        
        if "Global Quote" in data:
            quote = data["Global Quote"]
            return {
                "symbol": quote.get("01. symbol", symbol),
                "price": float(quote.get("05. price", 0)),
                "volume": int(quote.get("06. volume", 0)),
                "latest_trading_day": quote.get("07. latest trading day", ""),
                "previous_close": float(quote.get("08. previous close", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%"),
                "open": float(quote.get("02. open", 0)),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0))
            }
        
        return {}
    
    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get fundamental data for a company.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Company overview including P/E ratio, market cap, etc.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol
        }
        
        data = await self._make_request(params)
        
        if data and "Symbol" in data:
            return {
                "symbol": data.get("Symbol", symbol),
                "name": data.get("Name", ""),
                "description": data.get("Description", ""),
                "exchange": data.get("Exchange", ""),
                "sector": data.get("Sector", ""),
                "industry": data.get("Industry", ""),
                "market_cap": int(data.get("MarketCapitalization", 0)),
                "pe_ratio": float(data.get("PERatio", 0)) if data.get("PERatio") != "None" else 0,
                "peg_ratio": float(data.get("PEGRatio", 0)) if data.get("PEGRatio") != "None" else 0,
                "book_value": float(data.get("BookValue", 0)) if data.get("BookValue") != "None" else 0,
                "dividend_yield": float(data.get("DividendYield", 0)) if data.get("DividendYield") != "None" else 0,
                "eps": float(data.get("EPS", 0)) if data.get("EPS") != "None" else 0,
                "revenue_per_share": float(data.get("RevenuePerShareTTM", 0)) if data.get("RevenuePerShareTTM") != "None" else 0,
                "profit_margin": float(data.get("ProfitMargin", 0)) if data.get("ProfitMargin") != "None" else 0,
                "operating_margin": float(data.get("OperatingMarginTTM", 0)) if data.get("OperatingMarginTTM") != "None" else 0,
                "return_on_assets": float(data.get("ReturnOnAssetsTTM", 0)) if data.get("ReturnOnAssetsTTM") != "None" else 0,
                "return_on_equity": float(data.get("ReturnOnEquityTTM", 0)) if data.get("ReturnOnEquityTTM") != "None" else 0,
                "revenue": int(data.get("RevenueTTM", 0)) if data.get("RevenueTTM") != "None" else 0,
                "gross_profit": int(data.get("GrossProfitTTM", 0)) if data.get("GrossProfitTTM") != "None" else 0,
                "52_week_high": float(data.get("52WeekHigh", 0)) if data.get("52WeekHigh") != "None" else 0,
                "52_week_low": float(data.get("52WeekLow", 0)) if data.get("52WeekLow") != "None" else 0,
                "50_day_moving_avg": float(data.get("50DayMovingAverage", 0)) if data.get("50DayMovingAverage") != "None" else 0,
                "200_day_moving_avg": float(data.get("200DayMovingAverage", 0)) if data.get("200DayMovingAverage") != "None" else 0,
                "analyst_target_price": float(data.get("AnalystTargetPrice", 0)) if data.get("AnalystTargetPrice") != "None" else 0,
                "beta": float(data.get("Beta", 1)) if data.get("Beta") != "None" else 1
            }
        
        return {}
    
    async def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Get technical indicators for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Technical indicators including RSI, MACD, etc.
        """
        indicators = {}
        
        # Get RSI
        params = {
            "function": "RSI",
            "symbol": symbol,
            "interval": "daily",
            "time_period": "14",
            "series_type": "close"
        }
        
        data = await self._make_request(params)
        if "Technical Analysis: RSI" in data:
            rsi_data = data["Technical Analysis: RSI"]
            if rsi_data:
                latest_date = list(rsi_data.keys())[0]
                indicators["rsi"] = float(rsi_data[latest_date]["RSI"])
        
        # Get SMA (50 day)
        params = {
            "function": "SMA",
            "symbol": symbol,
            "interval": "daily",
            "time_period": "50",
            "series_type": "close"
        }
        
        data = await self._make_request(params)
        if "Technical Analysis: SMA" in data:
            sma_data = data["Technical Analysis: SMA"]
            if sma_data:
                latest_date = list(sma_data.keys())[0]
                indicators["sma_50"] = float(sma_data[latest_date]["SMA"])
        
        return indicators
    
    async def get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get news sentiment for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            News sentiment data
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "limit": "10"
        }
        
        data = await self._make_request(params)
        
        if "feed" in data:
            articles = data["feed"]
            
            if articles:
                # Calculate average sentiment
                sentiments = []
                for article in articles:
                    for ticker_sentiment in article.get("ticker_sentiment", []):
                        if ticker_sentiment.get("ticker") == symbol:
                            score = float(ticker_sentiment.get("ticker_sentiment_score", 0))
                            sentiments.append(score)
                
                avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
                
                return {
                    "sentiment_score": avg_sentiment,
                    "sentiment_label": self._get_sentiment_label(avg_sentiment),
                    "article_count": len(articles),
                    "articles": [
                        {
                            "title": a.get("title", ""),
                            "url": a.get("url", ""),
                            "time_published": a.get("time_published", ""),
                            "source": a.get("source", "")
                        }
                        for a in articles[:3]  # Return top 3 articles
                    ]
                }
        
        return {}
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.15:
            return "Bullish"
        elif score <= -0.15:
            return "Bearish"
        else:
            return "Neutral"
    
    def has_api_key(self) -> bool:
        """Check if API key is available"""
        return bool(self.api_key)
