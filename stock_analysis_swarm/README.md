# Stock Analysis Agentic Swarm 📈

A sophisticated multi-agent system for comprehensive stock market analysis and research.

## ⚠️ DISCLAIMER
This system is for **research and educational purposes only**. It does NOT provide financial advice. All investment decisions should be made with proper due diligence and professional consultation.

## Overview

The Stock Analysis Swarm is a distributed agent system that:
- Aggregates data from multiple financial sources
- Performs technical and fundamental analysis
- Monitors social sentiment and insider activity
- Tracks political and regulatory changes
- Provides comprehensive research reports

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│                 (Supreme Market Commander)                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
    ┌─────────────┴─────────────┬──────────────┬──────────────┐
    ▼                           ▼              ▼              ▼
┌──────────┐          ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ PLANNER  │          │  RESEARCHER  │  │ SCANNER  │  │ ANALYST  │
│  AGENT   │          │    SWARM     │  │  SWARM   │  │  SWARM   │
└──────────┘          └──────────────┘  └──────────┘  └──────────┘
```

## Quick Start

### Prerequisites
- Python 3.9+
- Poetry (for dependency management)
- API keys for data sources (see Configuration)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd stock_analysis_swarm

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Create a `.env` file with the following API keys:

```env
# Financial Data APIs
ALPHA_VANTAGE_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here

# Social Media APIs
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
TWITTER_API_KEY=your_key_here
TWITTER_API_SECRET=your_secret_here

# Research APIs
TAVILY_API_KEY=your_key_here
GOOGLE_SEARCH_API_KEY=your_key_here
PERPLEXITY_API_KEY=your_key_here

# Regulatory Data
QUIVER_QUANT_API_KEY=your_key_here
```

### Basic Usage

```python
from stock_swarm import StockOrchestratorAgent

# Initialize the orchestrator
orchestrator = StockOrchestratorAgent()
await orchestrator.initialize()

# Analyze a stock
analysis = await orchestrator.analyze_stock("AAPL", depth="full")

# Get the report
print(analysis.summary)
```

## Features

### Research Agents
- **Fundamental Analysis**: Financial metrics, earnings, company info
- **Technical Analysis**: Chart patterns, indicators, price action
- **Sentiment Analysis**: News, social media, analyst ratings
- **Social Intelligence**: Reddit, Twitter, StockTwits monitoring
- **Political Tracking**: Congress trades, regulatory changes
- **Insider Monitoring**: Form 4 filings, institutional changes

### Scanner Network
- **Market Scanner**: Unusual volume, price breakouts
- **Options Flow**: Unusual activity, put/call ratios
- **Short Interest**: Squeeze potential, borrow rates

### Analysis & Synthesis
- **Pattern Recognition**: Historical patterns, correlations
- **Risk Analysis**: VaR, beta, stress testing
- **Opportunity Scoring**: Multi-factor analysis

## Project Structure

```
stock_analysis_swarm/
├── src/
│   ├── agents/           # Agent implementations
│   │   ├── core/         # Base agent classes
│   │   ├── research/     # Research agents
│   │   ├── scanners/     # Scanner agents
│   │   └── analysis/     # Analysis agents
│   ├── integrations/     # API integrations
│   ├── knowledge_graph/  # KG integration
│   └── utils/            # Utilities
├── tests/                # Test suite
├── docs/                 # Documentation
└── examples/             # Usage examples
```

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
poetry run black .
poetry run flake8
poetry run mypy .
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

For issues and questions, please open a GitHub issue.

---

**Remember**: This is for research and educational purposes only. Not financial advice!
