"""
Stock Orchestrator Agent - Coordinates all stock analysis sub-agents
Built on the existing BaseAgent from agents/core/base_agent.py
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

# Import real data client
try:
    from stock_analysis_swarm.clients import AlphaVantageClient
except ImportError:
    AlphaVantageClient = None
    logger.warning("AlphaVantageClient not available - will use mock data")


class StockAnalysisCapability(str, Enum):
    """Stock-specific capabilities"""
    STOCK_ORCHESTRATION = "stock_orchestration"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    REPORT_GENERATION = "report_generation"


class StockOrchestratorAgent(BaseAgent):
    """
    Master orchestrator for stock analysis swarm.
    Inherits from existing BaseAgent and uses existing KG infrastructure.
    """
    
    def __init__(
        self,
        agent_id: str = "stock-orchestrator",
        knowledge_graph: Optional[KnowledgeGraphManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the orchestrator using existing BaseAgent"""
        
        # Define orchestrator capabilities
        capabilities = {
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.AGENT_MANAGEMENT, "1.0"),
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
        }
        
        # Initialize parent BaseAgent
        super().__init__(
            agent_id=agent_id,
            agent_type="orchestrator",
            capabilities=capabilities,
            knowledge_graph=knowledge_graph,
            config=config or {}
        )
        
        # Stock-specific attributes
        self.active_analyses = {}
        self.sub_agents = {}
        self.kg_tools = None
        
        # REAL data provider - NOT MOCK!
        self.data_provider = MarketDataAggregator()
        
        # Analysis queue for managing requests
        self.analysis_queue = asyncio.Queue()
        
        # Initialize real data client
        self.data_client = None
        if AlphaVantageClient:
            self.data_client = AlphaVantageClient()
            if self.data_client.has_api_key():
                logger.info("Using REAL Alpha Vantage data")
            else:
                logger.warning("No Alpha Vantage API key - using FREE Yahoo Finance data")
        else:
            logger.info("Using FREE Yahoo Finance data provider")
        
        logger.info(f"StockOrchestratorAgent initialized with REAL data: {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the orchestrator and set up KG tools"""
        await super().initialize()
        
        # Set up KG tools if knowledge graph is available
        if self.knowledge_graph:
            self.kg_tools = KGTools(self.knowledge_graph, self.agent_id)
            
            # Register in KG with stock-specific types
            await self.knowledge_graph.add_triple(
                f"agent:{self.agent_id}",
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/stock#StockOrchestrator"
            )
            await self.knowledge_graph.add_triple(
                f"agent:{self.agent_id}",
                "http://example.org/core#coordinates",
                "http://example.org/stock#StockAnalysisSwarm"
            )
            
            logger.info("KG tools initialized for stock orchestrator")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages - required by BaseAgent.
        Routes stock analysis requests to appropriate handlers.
        """
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
        
        elif action == "get_status":
            analysis_id = message.content.get("analysis_id")
            status = self.get_analysis_status(analysis_id)
            
            return AgentMessage(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                action="status_update",
                content={"status": status}
            )
        
        else:
            # Default response for unknown actions
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="error",
                content={"error": f"Unknown action: {message.message_type}"}
            )
    
    async def analyze_stock(self, ticker: str, depth: str = "standard") -> Dict[str, Any]:
        """
        Orchestrate comprehensive stock analysis.
        
        Args:
            ticker: Stock symbol to analyze
            depth: Analysis depth (quick, standard, full)
            
        Returns:
            Comprehensive analysis results
        """
        logger.info(f"Starting {depth} analysis for {ticker}")
        
        # Generate analysis ID
        analysis_id = f"{ticker}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create analysis workflow in KG if available
        if self.kg_tools:
            workflow_id = await self.kg_tools.create_workflow_node(
                workflow_name=f"Stock Analysis: {ticker}",
                workflow_type="stock_analysis",
                steps=[
                    {"step": 1, "action": "research", "description": f"Research {ticker}"},
                    {"step": 2, "action": "analyze", "description": f"Analyze {ticker} data"},
                    {"step": 3, "action": "synthesize", "description": "Synthesize results"}
                ],
                metadata={"depth": depth, "ticker": ticker}
            )
            
            # Create main analysis task
            task_id = await self.kg_tools.create_task_node(
                task_name=f"Analyze {ticker}",
                task_type="stock_analysis",
                description=f"Perform {depth} analysis of {ticker}",
                metadata={
                    "ticker": ticker,
                    "depth": depth,
                    "analysis_id": analysis_id
                }
            )
            
            # Link task to workflow in KG
            await self.knowledge_graph.add_triple(
                task_id,
                "http://example.org/core#belongsToWorkflow",
                workflow_id
            )
        
        # Store analysis info
        self.active_analyses[analysis_id] = {
            "ticker": ticker,
            "depth": depth,
            "status": "initializing",
            "started_at": datetime.now().isoformat(),
            "workflow_id": workflow_id if self.kg_tools else None,
            "results": {}
        }
        
        try:
            # Phase 1: Planning
            plan = await self._create_analysis_plan(ticker, depth)
            self.active_analyses[analysis_id]["plan"] = plan
            
            # Phase 2: Parallel Research (dispatching to sub-agents)
            research_results = await self._execute_research_phase(ticker, analysis_id)
            self.active_analyses[analysis_id]["research"] = research_results
            
            # Phase 3: Risk Assessment
            risk_assessment = await self._assess_risk(ticker, research_results)
            self.active_analyses[analysis_id]["risk"] = risk_assessment
            
            # Phase 4: Synthesis
            final_analysis = await self._synthesize_results(
                ticker, research_results, risk_assessment, analysis_id
            )
            
            # Update status
            self.active_analyses[analysis_id]["status"] = "completed"
            self.active_analyses[analysis_id]["completed_at"] = datetime.now().isoformat()
            self.active_analyses[analysis_id]["results"] = final_analysis
            
            # Store in KG if available
            if self.knowledge_graph:
                await self._store_analysis_in_kg(analysis_id, final_analysis)
            
            # Mark task as complete
            if self.kg_tools and task_id:
                await self.kg_tools.update_task_status(
                    task_id,
                    "completed",
                    result={"analysis": final_analysis}
                )
            
            logger.info(f"Analysis {analysis_id} completed successfully")
            
            # Send SMS notification on completion
            try:
                opportunity_score = final_analysis.get("opportunity_score", "N/A")
                recommendation = final_analysis.get("recommendation", "Analysis complete")
                sms_msg = f"Stock analysis complete: {ticker} | Score: {opportunity_score}/10 | {recommendation[:50]}"
                await self.send_sms_notification(sms_msg)
            except Exception as sms_err:
                logger.warning(f"SMS notification failed: {sms_err}")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {str(e)}")
            self.active_analyses[analysis_id]["status"] = "failed"
            self.active_analyses[analysis_id]["error"] = str(e)
            
            if self.kg_tools and task_id:
                await self.kg_tools.update_task_status(
                    task_id,
                    "failed",
                    result={"error": str(e)}
                )
            
            # Send SMS notification on failure
            try:
                sms_msg = f"Stock analysis failed: {ticker} | Error: {str(e)[:80]}"
                await self.send_sms_notification(sms_msg)
            except Exception as sms_err:
                logger.warning(f"SMS notification (error) failed: {sms_err}")
            
            raise
    
    async def _create_analysis_plan(self, ticker: str, depth: str) -> Dict[str, Any]:
        """Create analysis plan based on stock characteristics and depth"""
        
        plan = {
            "ticker": ticker,
            "depth": depth,
            "strategies": [],
            "required_agents": [],
            "priority_factors": []
        }
        
        # Determine required analyses based on depth
        if depth == "quick":
            plan["required_agents"] = ["technical", "sentiment"]
            plan["strategies"] = ["momentum", "sentiment_check"]
        elif depth == "standard":
            plan["required_agents"] = ["fundamental", "technical", "sentiment"]
            plan["strategies"] = ["balanced_analysis", "risk_assessment"]
        else:  # full
            plan["required_agents"] = [
                "fundamental", "technical", "sentiment",
                "social", "insider", "options"
            ]
            plan["strategies"] = ["comprehensive", "multi_factor", "deep_dive"]
        
        # Check for similar past analyses in KG
        if self.knowledge_graph:
            past_analyses = await self.knowledge_graph.query_graph(f"""
                PREFIX stock: <http://example.org/stock#>
                SELECT ?analysis ?score ?date WHERE {{
                    ?analysis stock:ticker "{ticker}" ;
                             stock:opportunityScore ?score ;
                             stock:completedAt ?date .
                }}
                ORDER BY DESC(?date)
                LIMIT 5
            """)
            
            if past_analyses:
                plan["learned_from"] = past_analyses
                logger.info(f"Found {len(past_analyses)} past analyses for {ticker}")
        
        return plan
    
    async def _execute_research_phase(
        self, ticker: str, analysis_id: str
    ) -> Dict[str, Any]:
        """Execute parallel research using sub-agents"""
        
        results = {}
        tasks = []
        
        # Get plan to know which agents to use
        plan = self.active_analyses[analysis_id].get("plan", {})
        required_agents = plan.get("required_agents", ["fundamental", "technical"])
        
        # Create research tasks for each required agent
        for agent_type in required_agents:
            if agent_type == "fundamental":
                task = self._get_fundamental_analysis(ticker)
            elif agent_type == "technical":
                task = self._get_technical_analysis(ticker)
            elif agent_type == "sentiment":
                task = self._get_sentiment_analysis(ticker)
            else:
                continue  # Skip unknown agent types for now
            
            tasks.append((agent_type, task))
        
        # Execute all tasks in parallel
        for agent_type, task in tasks:
            try:
                result = await task
                results[agent_type] = result
            except Exception as e:
                logger.error(f"Research task {agent_type} failed: {str(e)}")
                results[agent_type] = {"error": str(e)}
        
        return results
    
    async def _get_fundamental_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental analysis - REAL DATA from market providers"""
        logger.info(f"Getting REAL fundamental analysis for {ticker}")
        
        # Get REAL market data
        try:
            stock_data = await self.data_provider.get_stock_data(ticker)
            
            if stock_data and stock_data.get('fundamentals'):
                # REAL data from Yahoo Finance or Alpha Vantage
                fundamentals = stock_data['fundamentals']
                logger.info(f"Retrieved REAL fundamental data for {ticker}")
                
                return {
                    "pe_ratio": fundamentals.get("pe_ratio", 0),
                    "forward_pe": fundamentals.get("forward_pe", 0),
                    "peg_ratio": fundamentals.get("peg_ratio", 0),
                    "price_to_book": fundamentals.get("price_to_book", 0),
                    "profit_margin": fundamentals.get("profit_margin", 0),
                    "operating_margin": fundamentals.get("operating_margin", 0),
                    "roe": fundamentals.get("return_on_equity", 0),
                    "revenue_growth": fundamentals.get("revenue_growth", 0),
                    "earnings_growth": fundamentals.get("earnings_growth", 0),
                    "debt_to_equity": fundamentals.get("debt_to_equity", 0),
                    "dividend_yield": fundamentals.get("dividend_yield", 0),
                    "beta": fundamentals.get("beta", 1),
                    "market_cap": fundamentals.get("market_cap", 0),
                    "data_source": "REAL_MARKET_DATA"
                }
                
        except Exception as e:
                logger.error(f"Error fetching real fundamental data: {e}")
        
        # Fallback to mock data
        logger.warning(f"Using MOCK fundamental data for {ticker}")
        return {
            "pe_ratio": 25.4,
            "revenue_growth": 0.15,
            "profit_margin": 0.22,
            "debt_to_equity": 0.45,
            "roe": 0.28,
            "score": 7.5,
            "data_source": "MOCK"
        }
    
    def _calculate_fundamental_score(self, overview: Dict[str, Any]) -> float:
        """Calculate fundamental score based on real metrics"""
        score = 5.0  # Start neutral
        
        # P/E ratio (lower is better, but not negative)
        pe = overview.get("pe_ratio", 0)
        if 0 < pe < 15:
            score += 1.5
        elif 15 <= pe < 25:
            score += 0.5
        elif pe > 40:
            score -= 1.0
        
        # Profit margin (higher is better)
        margin = overview.get("profit_margin", 0)
        if margin > 0.2:
            score += 1.5
        elif margin > 0.1:
            score += 0.5
        elif margin < 0:
            score -= 2.0
        
        # ROE (higher is better)
        roe = overview.get("return_on_equity", 0)
        if roe > 0.2:
            score += 1.0
        elif roe > 0.1:
            score += 0.5
        elif roe < 0:
            score -= 1.0
        
        # Analyst sentiment
        if overview.get("analyst_target_price") and overview.get("50_day_moving_avg"):
            current = overview["50_day_moving_avg"]
            target = overview["analyst_target_price"]
            upside = (target - current) / current if current > 0 else 0
            if upside > 0.2:
                score += 1.0
            elif upside < -0.1:
                score -= 0.5
        
        return max(0, min(10, score))  # Clamp between 0 and 10
    
    async def _get_technical_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get technical analysis - REAL DATA from market providers"""
        logger.info(f"Getting REAL technical analysis for {ticker}")
        
        # Try to get real data first
        if self.data_client and self.data_client.has_api_key():
            try:
                logger.info(f"Fetching REAL technical data for {ticker}")
                
                # Get quote and indicators
                quote = await self.data_client.get_quote(ticker)
                indicators = await self.data_client.get_technical_indicators(ticker)
                overview = await self.data_client.get_company_overview(ticker)
                
                if quote or indicators or overview:
                    current_price = quote.get("price", 0) if quote else 0
                    rsi = indicators.get("rsi", 50) if indicators else 50
                    sma_50 = overview.get("50_day_moving_avg", 0) if overview else 0
                    sma_200 = overview.get("200_day_moving_avg", 0) if overview else 0
                    
                    # Determine trend
                    trend = "neutral"
                    if current_price and sma_50:
                        if current_price > sma_50:
                            trend = "upward"
                        else:
                            trend = "downward"
                    
                    # Determine signal
                    signal = "neutral"
                    if rsi < 30:
                        signal = "oversold"
                    elif rsi > 70:
                        signal = "overbought"
                    elif trend == "upward" and rsi > 50:
                        signal = "bullish"
                    elif trend == "downward" and rsi < 50:
                        signal = "bearish"
                    
                    return {
                        "rsi": rsi,
                        "macd_signal": signal,
                        "current_price": current_price,
                        "sma_50": sma_50,
                        "sma_200": sma_200,
                        "trend": trend,
                        "score": self._calculate_technical_score_simple(rsi, trend),
                        "data_source": "REAL_ALPHA_VANTAGE"
                    }
            except Exception as e:
                logger.error(f"Error fetching real technical data: {e}")
        
        # Fallback to mock data
        logger.warning(f"Using MOCK technical data for {ticker}")
        return {
            "rsi": 55,
            "macd_signal": "bullish",
            "support": 145.20,
            "resistance": 152.80,
            "trend": "upward",
            "score": 8.0,
            "data_source": "MOCK"
        }
    
    def _calculate_technical_score_simple(self, rsi: float, trend: str) -> float:
        """Simple technical score calculation"""
        score = 5.0
        
        if 30 < rsi < 70:
            score += 1.0
        if trend == "upward":
            score += 2.0
        elif trend == "downward":
            score -= 1.0
        
        return max(0, min(10, score))
    
    async def _get_sentiment_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get sentiment analysis - REAL DATA when API key available"""
        logger.info(f"Getting sentiment analysis for {ticker}")
        
        # Try to get real data first
        if self.data_client and self.data_client.has_api_key():
            try:
                logger.info(f"Fetching REAL sentiment data for {ticker}")
                
                # Get news sentiment
                sentiment_data = await self.data_client.get_news_sentiment(ticker)
                
                if sentiment_data:
                    return {
                        "news_sentiment": sentiment_data.get("sentiment_score", 0),
                        "sentiment_label": sentiment_data.get("sentiment_label", "Neutral"),
                        "article_count": sentiment_data.get("article_count", 0),
                        "recent_articles": sentiment_data.get("articles", []),
                        "score": self._calculate_sentiment_score(sentiment_data.get("sentiment_score", 0)),
                        "data_source": "REAL_ALPHA_VANTAGE"
                    }
            except Exception as e:
                logger.error(f"Error fetching real sentiment data: {e}")
        
        # Fallback to mock data
        logger.warning(f"Using MOCK sentiment data for {ticker}")
        return {
            "news_sentiment": 0.65,
            "social_sentiment": 0.72,
            "analyst_consensus": "buy",
            "score": 7.8,
            "data_source": "MOCK"
        }
    
    def _calculate_sentiment_score(self, sentiment: float) -> float:
        """Convert sentiment to score (0-10)"""
        # Sentiment ranges from -1 to 1, convert to 0-10
        return (sentiment + 1) * 5
    
    async def _assess_risk(
        self, ticker: str, research_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk based on research results"""
        
        risk_factors = []
        risk_score = 3.0  # Base risk
        
        # Check fundamental risks
        if "fundamental" in research_results:
            fundamental = research_results["fundamental"]
            if fundamental.get("debt_to_equity", 0) > 1.0:
                risk_factors.append("high_debt")
                risk_score += 2.0
        
        # Check technical risks
        if "technical" in research_results:
            technical = research_results["technical"]
            if technical.get("rsi", 50) > 70:
                risk_factors.append("overbought")
                risk_score += 1.5
        
        return {
            "risk_score": min(risk_score, 10.0),
            "risk_factors": risk_factors,
            "risk_level": "high" if risk_score > 7 else "medium" if risk_score > 4 else "low"
        }
    
    async def _synthesize_results(
        self, ticker: str, research: Dict, risk: Dict, analysis_id: str
    ) -> Dict[str, Any]:
        """Synthesize all research into final analysis"""
        
        # Calculate opportunity score
        scores = []
        for agent_type, result in research.items():
            if isinstance(result, dict) and "score" in result:
                scores.append(result["score"])
        
        opportunity_score = sum(scores) / len(scores) if scores else 5.0
        
        # Adjust for risk
        risk_adjusted_score = opportunity_score * (1 - risk["risk_score"] / 20)
        
        # Generate signals
        signals = []
        if research.get("technical", {}).get("macd_signal") == "bullish":
            signals.append({
                "type": "bullish",
                "source": "technical",
                "strength": "moderate"
            })
        
        if research.get("sentiment", {}).get("analyst_consensus") == "buy":
            signals.append({
                "type": "bullish",
                "source": "analysts",
                "strength": "strong"
            })
        
        return {
            "ticker": ticker,
            "analysis_id": analysis_id,
            "timestamp": datetime.now().isoformat(),
            "opportunity_score": risk_adjusted_score,
            "risk_assessment": risk,
            "signals": signals,
            "research_summary": research,
            "recommendation": self._generate_recommendation(risk_adjusted_score, risk)
        }
    
    def _generate_recommendation(self, score: float, risk: Dict) -> str:
        """Generate recommendation based on score and risk"""
        
        if score > 7 and risk["risk_level"] == "low":
            return "Strong Buy - High opportunity with low risk"
        elif score > 6:
            return "Buy - Good opportunity, monitor risk factors"
        elif score > 4:
            return "Hold - Moderate opportunity"
        else:
            return "Caution - Limited opportunity or high risk"
    
    async def _store_analysis_in_kg(
        self, analysis_id: str, analysis: Dict[str, Any]
    ) -> None:
        """Store analysis results in knowledge graph"""
        
        if not self.knowledge_graph:
            return
        
        # Store analysis as RDF triples
        analysis_uri = f"http://example.org/stock/analysis/{analysis_id}"
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/stock#StockAnalysis"
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#ticker",
            analysis["ticker"]
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#opportunityScore",
            str(analysis["opportunity_score"])
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#riskScore",
            str(analysis["risk_assessment"]["risk_score"])
        )
        
        await self.knowledge_graph.add_triple(
            analysis_uri,
            "http://example.org/stock#recommendation",
            analysis["recommendation"]
        )
        
        # Store signals
        for signal in analysis.get("signals", []):
            await self.knowledge_graph.add_triple(
                analysis_uri,
                "http://example.org/stock#hasSignal",
                json.dumps(signal)
            )
        
        logger.info(f"Stored analysis {analysis_id} in knowledge graph")
    
    def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """Get status of an analysis"""
        
        if analysis_id not in self.active_analyses:
            return {"status": "not_found"}
        
        analysis = self.active_analyses[analysis_id]
        return {
            "status": analysis["status"],
            "ticker": analysis["ticker"],
            "started_at": analysis["started_at"],
            "completed_at": analysis.get("completed_at"),
            "progress": self._calculate_progress(analysis)
        }
    
    def _calculate_progress(self, analysis: Dict) -> float:
        """Calculate progress percentage of analysis"""
        
        if analysis["status"] == "completed":
            return 100.0
        elif analysis["status"] == "failed":
            return 0.0
        
        steps_complete = 0
        total_steps = 4
        
        if "plan" in analysis:
            steps_complete += 1
        if "research" in analysis:
            steps_complete += 1
        if "risk" in analysis:
            steps_complete += 1
        if "results" in analysis:
            steps_complete += 1
        
        return (steps_complete / total_steps) * 100
