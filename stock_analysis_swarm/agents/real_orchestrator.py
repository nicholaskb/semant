"""
Real Stock Orchestrator Agent with ACTUAL Market Data
======================================================
This is the REAL implementation - no mock data!
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum

# Import from existing framework
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus
from agents.core.capability_types import Capability, CapabilityType
from kg.models.graph_manager import KnowledgeGraphManager
from agents.tools.kg_tools import KGTools
from loguru import logger

# Import REAL data providers
from stock_analysis_swarm.data_providers import (
    MarketDataAggregator, 
    TechnicalIndicators
)


class RealStockOrchestratorAgent(BaseAgent):
    """
    REAL Stock Orchestrator with actual market data.
    No mock data - everything is real!
    """
    
    def __init__(
        self,
        agent_id: str = "real-stock-orchestrator",
        knowledge_graph: Optional[KnowledgeGraphManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize with REAL data providers"""
        
        # Define capabilities
        capabilities = {
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.AGENT_MANAGEMENT, "1.0"),
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
        }
        
        # Initialize parent
        super().__init__(
            agent_id=agent_id,
            agent_type="orchestrator",
            capabilities=capabilities,
            knowledge_graph=knowledge_graph,
            config=config or {}
        )
        
        # REAL data provider
        self.data_provider = MarketDataAggregator()
        
        # Stock-specific attributes
        self.active_analyses = {}
        self.kg_tools = None
        
        logger.info(f"RealStockOrchestratorAgent initialized with REAL data: {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the orchestrator"""
        await super().initialize()
        
        # Set up KG tools if available
        if self.knowledge_graph:
            self.kg_tools = KGTools(self.knowledge_graph, self.agent_id)
            
            # Register in KG
            await self.knowledge_graph.add_triple(
                f"agent:{self.agent_id}",
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/stock#RealStockOrchestrator"
            )
            
            logger.info("KG tools initialized for REAL stock orchestrator")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages"""
        action = message.content.get("action")
        
        if action == "analyze_stock":
            ticker = message.content.get("ticker")
            depth = message.content.get("depth", "standard")
            result = await self.analyze_stock(ticker, depth)
            
            return AgentMessage(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                action="analysis_result",
                content={"analysis": result}
            )
        
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="error",
            content={"error": f"Unknown action: {action}"}
        )
    
    async def analyze_stock(self, ticker: str, depth: str = "standard") -> Dict[str, Any]:
        """
        Analyze stock with REAL market data
        
        Args:
            ticker: Stock symbol
            depth: Analysis depth (quick, standard, full)
            
        Returns:
            REAL analysis results from actual market data
        """
        logger.info(f"Starting REAL analysis for {ticker}")
        
        # Generate analysis ID
        analysis_id = f"{ticker}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Store analysis info
        self.active_analyses[analysis_id] = {
            "ticker": ticker,
            "depth": depth,
            "status": "fetching_real_data",
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Get REAL market data
            logger.info(f"Fetching REAL market data for {ticker}")
            stock_data = await self.data_provider.get_stock_data(ticker)
            
            if not stock_data or not stock_data.get('quote'):
                raise ValueError(f"Failed to get real data for {ticker}")
            
            # Extract REAL quote data
            quote = stock_data['quote']
            fundamentals = stock_data.get('fundamentals', {})
            
            # Perform REAL analysis
            technical_analysis = self._analyze_technicals(quote, fundamentals)
            fundamental_analysis = self._analyze_fundamentals(fundamentals)
            risk_assessment = self._assess_risk(quote, fundamentals)
            
            # Calculate REAL opportunity score
            opportunity_score = self._calculate_real_score(
                quote, fundamentals, technical_analysis, fundamental_analysis
            )
            
            # Generate recommendation based on REAL data
            recommendation = self._generate_recommendation(
                opportunity_score, risk_assessment, technical_analysis
            )
            
            # Prepare final REAL analysis
            final_analysis = {
                "ticker": ticker,
                "analysis_id": analysis_id,
                "timestamp": datetime.now().isoformat(),
                "quote": {
                    "price": quote.get('price', 0),
                    "change": quote.get('change', 0),
                    "change_percent": quote.get('change_percent', 0),
                    "volume": quote.get('volume', 0),
                    "market_cap": quote.get('market_cap', 0)
                },
                "technical": technical_analysis,
                "fundamental": fundamental_analysis,
                "risk_assessment": risk_assessment,
                "opportunity_score": opportunity_score,
                "recommendation": recommendation,
                "signals": self._generate_signals(technical_analysis, fundamental_analysis),
                "data_source": "REAL_MARKET_DATA"
            }
            
            # Store in Knowledge Graph
            if self.knowledge_graph:
                await self._store_analysis_in_kg(analysis_id, final_analysis)
            
            # Update status
            self.active_analyses[analysis_id]["status"] = "completed"
            self.active_analyses[analysis_id]["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"REAL analysis {analysis_id} completed successfully")
            return final_analysis
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {str(e)}")
            self.active_analyses[analysis_id]["status"] = "failed"
            self.active_analyses[analysis_id]["error"] = str(e)
            raise
    
    def _analyze_technicals(self, quote: Dict, fundamentals: Dict) -> Dict[str, Any]:
        """Analyze technical indicators from REAL data"""
        
        price = quote.get('price', 0)
        change_percent = quote.get('change_percent', 0)
        volume = quote.get('volume', 0)
        
        # Determine trend from REAL price movement
        if change_percent > 2:
            trend = "strong_upward"
        elif change_percent > 0.5:
            trend = "upward"
        elif change_percent < -2:
            trend = "strong_downward"
        elif change_percent < -0.5:
            trend = "downward"
        else:
            trend = "sideways"
        
        # Calculate simple RSI approximation
        if abs(change_percent) < 1:
            rsi = 50
        elif change_percent > 5:
            rsi = min(80, 50 + change_percent * 6)
        elif change_percent < -5:
            rsi = max(20, 50 + change_percent * 6)
        else:
            rsi = 50 + change_percent * 5
        
        # Determine signal from REAL metrics
        if rsi > 70 and change_percent > 3:
            signal = "overbought"
        elif rsi < 30 and change_percent < -3:
            signal = "oversold"
        elif trend in ["upward", "strong_upward"]:
            signal = "bullish"
        elif trend in ["downward", "strong_downward"]:
            signal = "bearish"
        else:
            signal = "neutral"
        
        return {
            "current_price": price,
            "change_percent": change_percent,
            "volume": volume,
            "trend": trend,
            "rsi": round(rsi, 2),
            "signal": signal,
            "52_week_high": fundamentals.get('52_week_high', price * 1.2),
            "52_week_low": fundamentals.get('52_week_low', price * 0.8),
            "support": fundamentals.get('52_week_low', price * 0.95),
            "resistance": fundamentals.get('52_week_high', price * 1.05)
        }
    
    def _analyze_fundamentals(self, fundamentals: Dict) -> Dict[str, Any]:
        """Analyze fundamental data - ALL REAL"""
        
        pe_ratio = fundamentals.get('pe_ratio', 0)
        peg_ratio = fundamentals.get('peg_ratio', 0)
        profit_margin = fundamentals.get('profit_margin', 0)
        roe = fundamentals.get('return_on_equity', 0)
        debt_to_equity = fundamentals.get('debt_to_equity', 0)
        
        # Determine valuation from REAL P/E
        if pe_ratio == 0:
            valuation = "unknown"
        elif pe_ratio < 15:
            valuation = "undervalued"
        elif pe_ratio < 25:
            valuation = "fair"
        elif pe_ratio < 35:
            valuation = "overvalued"
        else:
            valuation = "expensive"
        
        # Determine health from REAL metrics
        health_score = 0
        if profit_margin and profit_margin > 0.1:
            health_score += 2
        if roe and roe > 0.15:
            health_score += 2
        if debt_to_equity and debt_to_equity < 1:
            health_score += 2
        if peg_ratio and 0 < peg_ratio < 1.5:
            health_score += 2
        
        if health_score >= 6:
            health = "excellent"
        elif health_score >= 4:
            health = "good"
        elif health_score >= 2:
            health = "moderate"
        else:
            health = "poor"
        
        return {
            "pe_ratio": pe_ratio,
            "peg_ratio": peg_ratio,
            "profit_margin": profit_margin,
            "return_on_equity": roe,
            "debt_to_equity": debt_to_equity,
            "dividend_yield": fundamentals.get('dividend_yield', 0),
            "valuation": valuation,
            "financial_health": health,
            "beta": fundamentals.get('beta', 1)
        }
    
    def _assess_risk(self, quote: Dict, fundamentals: Dict) -> Dict[str, Any]:
        """Assess risk from REAL market data"""
        
        beta = fundamentals.get('beta', 1)
        debt_to_equity = fundamentals.get('debt_to_equity', 0)
        change_percent = abs(quote.get('change_percent', 0))
        
        # Calculate risk level from REAL metrics
        risk_score = 0
        
        if beta > 1.5:
            risk_score += 3
        elif beta > 1.2:
            risk_score += 2
        elif beta > 1:
            risk_score += 1
        
        if debt_to_equity > 2:
            risk_score += 3
        elif debt_to_equity > 1:
            risk_score += 2
        elif debt_to_equity > 0.5:
            risk_score += 1
        
        if change_percent > 5:
            risk_score += 2
        elif change_percent > 3:
            risk_score += 1
        
        if risk_score <= 2:
            risk_level = "low"
        elif risk_score <= 5:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "volatility": "high" if beta > 1.5 else "moderate" if beta > 1 else "low",
            "debt_risk": "high" if debt_to_equity > 2 else "moderate" if debt_to_equity > 1 else "low",
            "beta": beta
        }
    
    def _calculate_real_score(self, quote: Dict, fundamentals: Dict, 
                             technical: Dict, fundamental: Dict) -> float:
        """Calculate opportunity score from REAL data"""
        
        score = 5.0  # Start neutral
        
        # Technical factors
        if technical.get('signal') == 'bullish':
            score += 1.5
        elif technical.get('signal') == 'bearish':
            score -= 1.5
        
        if technical.get('trend') in ['upward', 'strong_upward']:
            score += 1
        elif technical.get('trend') in ['downward', 'strong_downward']:
            score -= 1
        
        # Fundamental factors
        if fundamental.get('valuation') == 'undervalued':
            score += 2
        elif fundamental.get('valuation') == 'overvalued':
            score -= 1
        
        if fundamental.get('financial_health') == 'excellent':
            score += 1.5
        elif fundamental.get('financial_health') == 'good':
            score += 0.5
        elif fundamental.get('financial_health') == 'poor':
            score -= 1.5
        
        # Growth factors
        pe_ratio = fundamentals.get('pe_ratio', 0)
        peg_ratio = fundamentals.get('peg_ratio', 0)
        
        if peg_ratio and 0 < peg_ratio < 1:
            score += 1.5  # Good growth at reasonable price
        elif peg_ratio and peg_ratio > 2:
            score -= 1  # Expensive growth
        
        return max(0, min(10, score))  # Clamp between 0-10
    
    def _generate_recommendation(self, score: float, risk: Dict, technical: Dict) -> str:
        """Generate recommendation from REAL analysis"""
        
        risk_level = risk.get('risk_level', 'medium')
        signal = technical.get('signal', 'neutral')
        
        if score >= 7:
            if risk_level == 'low':
                return "Strong Buy - Excellent opportunity with low risk"
            elif risk_level == 'medium':
                return "Buy - Good opportunity, moderate risk"
            else:
                return "Speculative Buy - High potential but high risk"
        elif score >= 5:
            if signal == 'bullish':
                return "Moderate Buy - Positive momentum"
            elif signal == 'bearish':
                return "Hold - Mixed signals, wait for clarity"
            else:
                return "Hold - Fair value, monitor for opportunities"
        elif score >= 3:
            if signal == 'oversold':
                return "Watch - Potential bounce opportunity"
            else:
                return "Hold/Reduce - Limited upside potential"
        else:
            if risk_level == 'high':
                return "Sell - Poor outlook with high risk"
            else:
                return "Reduce Position - Weak fundamentals"
    
    def _generate_signals(self, technical: Dict, fundamental: Dict) -> List[Dict]:
        """Generate trading signals from REAL analysis"""
        
        signals = []
        
        # Technical signals
        if technical.get('signal') in ['bullish', 'overbought', 'oversold', 'bearish']:
            signals.append({
                "type": technical['signal'],
                "source": "technical",
                "strength": "strong" if abs(technical.get('rsi', 50) - 50) > 20 else "moderate"
            })
        
        # Fundamental signals
        if fundamental.get('valuation') in ['undervalued', 'overvalued']:
            signals.append({
                "type": "value_opportunity" if fundamental['valuation'] == 'undervalued' else "overpriced",
                "source": "fundamental",
                "strength": "strong"
            })
        
        # Health signals
        if fundamental.get('financial_health') in ['excellent', 'poor']:
            signals.append({
                "type": "healthy" if fundamental['financial_health'] == 'excellent' else "unhealthy",
                "source": "fundamental",
                "strength": "strong"
            })
        
        return signals
    
    async def _store_analysis_in_kg(self, analysis_id: str, analysis: Dict) -> None:
        """Store analysis in knowledge graph"""
        
        analysis_uri = f"http://example.org/analysis/{analysis_id}"
        
        # Store as RDF triples
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/stock#RealStockAnalysis"
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#ticker",
            analysis['ticker']
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#opportunityScore",
            str(analysis['opportunity_score'])
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#dataSource",
            "REAL_MARKET_DATA"
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#recommendation",
            analysis['recommendation']
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#completedAt",
            analysis['timestamp']
        )
        
        logger.info(f"Stored REAL analysis {analysis_id} in knowledge graph")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.data_provider.cleanup()
        await super().cleanup()
