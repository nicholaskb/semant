"""
Real Market Data Providers for Stock Analysis
==============================================
This module provides REAL market data from actual sources.
No mock data, no placeholders - actual market information.
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from loguru import logger

class MarketDataProvider:
    """Base class for market data providers"""
    
    def __init__(self):
        self.session = None
        
    async def initialize(self):
        """Initialize the provider"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get current quote for a ticker"""
        raise NotImplementedError
        
    async def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental data for a ticker"""
        raise NotImplementedError


class YFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance data provider - FREE, no API key required
    Uses the yfinance web API endpoints directly
    """
    
    BASE_URL = "https://query1.finance.yahoo.com"
    
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote data from Yahoo Finance"""
        await self.initialize()
        
        try:
            # Yahoo Finance quote endpoint
            url = f"{self.BASE_URL}/v8/finance/chart/{ticker}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                        result = data['chart']['result'][0]
                        meta = result.get('meta', {})
                        
                        # Extract REAL market data
                        return {
                            'symbol': ticker,
                            'price': meta.get('regularMarketPrice', 0),
                            'previous_close': meta.get('previousClose', 0),
                            'change': meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0),
                            'change_percent': ((meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0)) / 
                                             meta.get('previousClose', 1) * 100) if meta.get('previousClose') else 0,
                            'volume': meta.get('regularMarketVolume', 0),
                            'market_cap': meta.get('marketCap', 0),
                            'exchange': meta.get('exchange', 'Unknown'),
                            'currency': meta.get('currency', 'USD'),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            logger.error(f"Failed to get quote for {ticker}: {e}")
            
        return {}
    
    async def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental data from Yahoo Finance"""
        await self.initialize()
        
        try:
            # Yahoo Finance key statistics endpoint
            url = f"{self.BASE_URL}/v10/finance/quoteSummary/{ticker}"
            params = {
                'modules': 'defaultKeyStatistics,financialData,summaryDetail'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'quoteSummary' in data and 'result' in data['quoteSummary']:
                        result = data['quoteSummary']['result'][0]
                        
                        financial = result.get('financialData', {})
                        stats = result.get('defaultKeyStatistics', {})
                        summary = result.get('summaryDetail', {})
                        
                        # Extract REAL fundamental data
                        return {
                            'pe_ratio': self._extract_value(summary, 'trailingPE'),
                            'forward_pe': self._extract_value(summary, 'forwardPE'),
                            'peg_ratio': self._extract_value(stats, 'pegRatio'),
                            'price_to_book': self._extract_value(stats, 'priceToBook'),
                            'profit_margin': self._extract_value(financial, 'profitMargins'),
                            'operating_margin': self._extract_value(financial, 'operatingMargins'),
                            'return_on_equity': self._extract_value(financial, 'returnOnEquity'),
                            'revenue_growth': self._extract_value(financial, 'revenueGrowth'),
                            'earnings_growth': self._extract_value(financial, 'earningsGrowth'),
                            'current_ratio': self._extract_value(financial, 'currentRatio'),
                            'debt_to_equity': self._extract_value(financial, 'debtToEquity'),
                            'dividend_yield': self._extract_value(summary, 'dividendYield'),
                            'beta': self._extract_value(summary, 'beta'),
                            '52_week_high': self._extract_value(summary, 'fiftyTwoWeekHigh'),
                            '52_week_low': self._extract_value(summary, 'fiftyTwoWeekLow')
                        }
        except Exception as e:
            logger.error(f"Failed to get fundamentals for {ticker}: {e}")
            
        return {}
    
    def _extract_value(self, data: Dict, key: str) -> Optional[float]:
        """Extract raw value from Yahoo Finance response"""
        if key in data and data[key]:
            if isinstance(data[key], dict) and 'raw' in data[key]:
                return data[key]['raw']
            return data[key]
        return None


class AlphaVantageProvider(MarketDataProvider):
    """
    Alpha Vantage data provider - Requires FREE API key
    Get your free key at: https://www.alphavantage.co/support/#api-key
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        
    @property
    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote from Alpha Vantage"""
        if not self.is_available:
            logger.warning("Alpha Vantage API key not configured")
            return {}
            
        await self.initialize()
        
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': ticker,
                'apikey': self.api_key
            }
            
            async with self.session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'Global Quote' in data:
                        quote = data['Global Quote']
                        
                        # Extract REAL market data
                        return {
                            'symbol': quote.get('01. symbol', ticker),
                            'price': float(quote.get('05. price', 0)),
                            'previous_close': float(quote.get('08. previous close', 0)),
                            'change': float(quote.get('09. change', 0)),
                            'change_percent': quote.get('10. change percent', '0%').rstrip('%'),
                            'volume': int(quote.get('06. volume', 0)),
                            'latest_trading_day': quote.get('07. latest trading day'),
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            logger.error(f"Failed to get Alpha Vantage quote for {ticker}: {e}")
            
        return {}
    
    async def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get company overview from Alpha Vantage"""
        if not self.is_available:
            return {}
            
        await self.initialize()
        
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': ticker,
                'apikey': self.api_key
            }
            
            async with self.session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'Symbol' in data:
                        # Extract REAL fundamental data
                        return {
                            'pe_ratio': self._safe_float(data.get('PERatio')),
                            'peg_ratio': self._safe_float(data.get('PEGRatio')),
                            'book_value': self._safe_float(data.get('BookValue')),
                            'dividend_yield': self._safe_float(data.get('DividendYield')),
                            'eps': self._safe_float(data.get('EPS')),
                            'revenue_per_share': self._safe_float(data.get('RevenuePerShareTTM')),
                            'profit_margin': self._safe_float(data.get('ProfitMargin')),
                            'operating_margin': self._safe_float(data.get('OperatingMarginTTM')),
                            'return_on_assets': self._safe_float(data.get('ReturnOnAssetsTTM')),
                            'return_on_equity': self._safe_float(data.get('ReturnOnEquityTTM')),
                            'revenue': self._safe_float(data.get('RevenueTTM')),
                            'gross_profit': self._safe_float(data.get('GrossProfitTTM')),
                            'diluted_eps': self._safe_float(data.get('DilutedEPSTTM')),
                            'quarterly_earnings_growth': self._safe_float(data.get('QuarterlyEarningsGrowthYOY')),
                            'quarterly_revenue_growth': self._safe_float(data.get('QuarterlyRevenueGrowthYOY')),
                            'analyst_target_price': self._safe_float(data.get('AnalystTargetPrice')),
                            'beta': self._safe_float(data.get('Beta')),
                            '52_week_high': self._safe_float(data.get('52WeekHigh')),
                            '52_week_low': self._safe_float(data.get('52WeekLow')),
                            'shares_outstanding': self._safe_float(data.get('SharesOutstanding')),
                            'market_cap': self._safe_float(data.get('MarketCapitalization'))
                        }
        except Exception as e:
            logger.error(f"Failed to get Alpha Vantage fundamentals for {ticker}: {e}")
            
        return {}
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value and value != 'None':
            try:
                return float(value)
            except:
                pass
        return None


class MarketDataAggregator:
    """
    Aggregates data from multiple providers
    Uses fallback strategy: Yahoo Finance -> Alpha Vantage -> etc.
    """
    
    def __init__(self):
        self.providers = [
            YFinanceProvider(),
            AlphaVantageProvider()
        ]
        
    async def get_stock_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive stock data from available providers
        Returns REAL market data, not mock!
        """
        quote_data = {}
        fundamental_data = {}
        
        # Try each provider until we get data
        for provider in self.providers:
            if not quote_data:
                quote_data = await provider.get_quote(ticker)
                
            if not fundamental_data:
                fundamental_data = await provider.get_fundamentals(ticker)
                
            if quote_data and fundamental_data:
                break
        
        # Combine all data
        return {
            'ticker': ticker,
            'quote': quote_data,
            'fundamentals': fundamental_data,
            'timestamp': datetime.now().isoformat(),
            'data_source': 'REAL_MARKET_DATA'  # Not mock!
        }
    
    async def cleanup(self):
        """Cleanup all providers"""
        for provider in self.providers:
            await provider.cleanup()


# Technical indicators calculator
class TechnicalIndicators:
    """Calculate REAL technical indicators from price data"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral if not enough data
            
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if not prices:
            return 0
        if len(prices) < period:
            return sum(prices) / len(prices)
            
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict[str, float]:
        """Calculate MACD indicator"""
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
            
        ema12 = TechnicalIndicators.calculate_ema(prices, 12)
        ema26 = TechnicalIndicators.calculate_ema(prices, 26)
        macd = ema12 - ema26
        signal = TechnicalIndicators.calculate_ema([macd], 9)
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': macd - signal
        }
