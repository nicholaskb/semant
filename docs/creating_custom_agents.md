# 🏗️ Creating Custom Agents

## Overview

This tutorial shows you how to create custom agents for the Semant multi-agent system. You'll learn to extend the BaseAgent class, implement capabilities, and integrate with the knowledge graph.

## Prerequisites

- Python 3.11+
- Familiarity with async/await
- Basic understanding of the Semant architecture

## Step 1: Plan Your Agent

### Define the Purpose
What will your agent do? Consider:
- **Data processing** (transform, analyze, validate)
- **External integrations** (APIs, databases, services)
- **Specialized tasks** (image processing, text analysis)

### Example: Weather Analysis Agent
We'll create an agent that:
- Fetches weather data from an API
- Analyzes weather patterns
- Stores results in the knowledge graph
- Provides weather-based recommendations

## Step 2: Create the Agent Class

### Basic Structure

```python
from typing import Dict, Any, List, Optional
from agents.core.base_agent import BaseAgent
from agents.core.message_types import AgentMessage
from loguru import logger
import asyncio
import aiohttp
import json
from datetime import datetime

class WeatherAnalysisAgent(BaseAgent):
    """
    Agent for analyzing weather data and providing insights.
    """

    CAPABILITIES = {
        "WEATHER_ANALYSIS",
        "DATA_FETCHING",
        "PATTERN_RECOGNITION"
    }

    def __init__(self, agent_id: str, api_key: Optional[str] = None):
        super().__init__(agent_id, "weather_analysis")

        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session: Optional[aiohttp.ClientSession] = None

        self.logger = logger.bind(agent_id=agent_id)
```

### Implement Required Methods

```python
async def initialize(self) -> None:
    """Initialize the agent and its dependencies."""
    try:
        await super().initialize()

        # Create HTTP session for API calls
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        # Register agent in knowledge graph
        if self.knowledge_graph:
            await self.knowledge_graph.add_triple(
                f"agent:{self.agent_id}",
                "rdf:type",
                "WeatherAnalysisAgent"
            )

        # Validate API key
        if not self.api_key:
            raise ValueError("Weather API key is required")

        self.logger.info("Weather Analysis Agent initialized")

    except Exception as e:
        self.logger.error(f"Failed to initialize WeatherAnalysisAgent: {e}")
        raise

async def shutdown(self) -> None:
    """Clean shutdown of the agent."""
    self.logger.info(f"Shutting down WeatherAnalysisAgent {self.agent_id}")

    # Close HTTP session
    if self.session:
        await self.session.close()

    await super().shutdown()

async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
    """Process incoming messages."""
    try:
        if message.message_type == "analyze_weather":
            return await self._handle_weather_analysis(message)
        elif message.message_type == "get_forecast":
            return await self._handle_forecast_request(message)
        elif message.message_type == "weather_alert":
            return await self._handle_weather_alert(message)
        else:
            return await self._handle_unknown_message(message)
    except Exception as e:
        self.logger.error(f"Error processing message: {e}")
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"error": str(e), "status": "error"},
            message_type="error_response",
            timestamp=datetime.now()
        )
```

## Step 3: Implement Agent Methods

### Weather Data Fetching

```python
async def _fetch_weather_data(self, city: str) -> Dict[str, Any]:
    """
    Fetch current weather data for a city.

    Args:
        city: City name (e.g., "New York", "London,UK")

    Returns:
        Weather data dictionary
    """
    if not self.session:
        raise RuntimeError("Agent not properly initialized")

    url = f"{self.base_url}/weather"
    params = {
        "q": city,
        "appid": self.api_key,
        "units": "metric"
    }

    async with self.session.get(url, params=params) as response:
        if response.status != 200:
            error_data = await response.json()
            raise ValueError(f"Weather API error: {error_data.get('message', 'Unknown error')}")

        return await response.json()

async def _fetch_forecast_data(self, city: str, days: int = 5) -> Dict[str, Any]:
    """
    Fetch weather forecast for a city.

    Args:
        city: City name
        days: Number of days for forecast (max 5)

    Returns:
        Forecast data dictionary
    """
    if not self.session:
        raise RuntimeError("Agent not properly initialized")

    url = f"{self.base_url}/forecast"
    params = {
        "q": city,
        "appid": self.api_key,
        "units": "metric",
        "cnt": min(days * 8, 40)  # API returns 3-hour intervals
    }

    async with self.session.get(url, params=params) as response:
        if response.status != 200:
            error_data = await response.json()
            raise ValueError(f"Forecast API error: {error_data.get('message', 'Unknown error')}")

        return await response.json()
```

### Weather Analysis Logic

```python
async def _analyze_weather_patterns(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze weather data for patterns and insights.

    Args:
        weather_data: Raw weather data from API

    Returns:
        Analysis results
    """
    analysis = {
        "temperature_trend": "stable",
        "humidity_level": "moderate",
        "wind_conditions": "calm",
        "recommendations": [],
        "alerts": []
    }

    # Temperature analysis
    temp = weather_data["main"]["temp"]
    if temp > 30:
        analysis["recommendations"].append("Stay hydrated and avoid prolonged sun exposure")
        analysis["alerts"].append("High temperature warning")
    elif temp < 0:
        analysis["recommendations"].append("Wear warm clothing")
        analysis["alerts"].append("Freezing conditions")

    # Humidity analysis
    humidity = weather_data["main"]["humidity"]
    if humidity > 80:
        analysis["humidity_level"] = "high"
        analysis["recommendations"].append("Use dehumidifier if indoors")
    elif humidity < 30:
        analysis["humidity_level"] = "low"
        analysis["recommendations"].append("Use humidifier to prevent dry skin")

    # Wind analysis
    wind_speed = weather_data["wind"]["speed"]
    if wind_speed > 10:
        analysis["wind_conditions"] = "windy"
        analysis["recommendations"].append("Secure loose objects outdoors")

    return analysis

async def _generate_weather_insights(self, current_weather: Dict, forecast: Dict) -> Dict[str, Any]:
    """
    Generate insights by combining current weather and forecast.

    Args:
        current_weather: Current weather data
        forecast: Forecast data

    Returns:
        Weather insights and recommendations
    """
    insights = {
        "short_term": {},
        "recommendations": [],
        "preparedness": []
    }

    # Analyze temperature trend
    current_temp = current_weather["main"]["temp"]
    forecast_temps = [item["main"]["temp"] for item in forecast["list"][:8]]  # Next 24 hours

    if forecast_temps:
        avg_forecast_temp = sum(forecast_temps) / len(forecast_temps)
        temp_change = avg_forecast_temp - current_temp

        if abs(temp_change) > 5:
            direction = "warmer" if temp_change > 0 else "cooler"
            insights["short_term"]["temperature"] = f"Temperature will be {direction} by {abs(temp_change):.1f}°C"
            insights["preparedness"].append(f"Prepare for {direction} weather")

    # Check for precipitation
    rain_items = [item for item in forecast["list"] if "rain" in item]
    if rain_items:
        insights["short_term"]["precipitation"] = "Rain expected in the next 24 hours"
        insights["preparedness"].append("Carry an umbrella")
        insights["recommendations"].append("Check for flooding in low-lying areas")

    return insights
```

## Step 4: Implement Message Handlers

### Weather Analysis Handler

```python
async def _handle_weather_analysis(self, message: AgentMessage) -> AgentMessage:
    """Handle weather analysis requests."""
    try:
        city = message.content.get("city")
        if not city:
            raise ValueError("City parameter is required")

        # Fetch weather data
        weather_data = await self._fetch_weather_data(city)
        forecast_data = await self._fetch_forecast_data(city)

        # Analyze patterns
        analysis = await self._analyze_weather_patterns(weather_data)
        insights = await self._generate_weather_insights(weather_data, forecast_data)

        # Store in knowledge graph
        if self.knowledge_graph:
            await self._store_weather_analysis(city, weather_data, analysis, insights)

        # Combine results
        result = {
            "city": city,
            "current_weather": {
                "temperature": weather_data["main"]["temp"],
                "humidity": weather_data["main"]["humidity"],
                "wind_speed": weather_data["wind"]["speed"],
                "description": weather_data["weather"][0]["description"],
                "timestamp": weather_data["dt"]
            },
            "analysis": analysis,
            "insights": insights,
            "status": "success"
        }

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=result,
            message_type="weather_analysis_response",
            timestamp=datetime.now()
        )

    except Exception as e:
        self.logger.error(f"Weather analysis failed: {e}")
        raise
```

### Forecast Handler

```python
async def _handle_forecast_request(self, message: AgentMessage) -> AgentMessage:
    """Handle forecast requests."""
    try:
        city = message.content.get("city")
        days = message.content.get("days", 3)

        if not city:
            raise ValueError("City parameter is required")

        forecast_data = await self._fetch_forecast_data(city, days)

        # Process forecast into daily summaries
        daily_forecasts = self._process_forecast_data(forecast_data)

        result = {
            "city": city,
            "forecast": daily_forecasts,
            "status": "success"
        }

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=result,
            message_type="forecast_response",
            timestamp=datetime.now()
        )

    except Exception as e:
        self.logger.error(f"Forecast request failed: {e}")
        raise
```

### Knowledge Graph Integration

```python
async def _store_weather_analysis(
    self,
    city: str,
    weather_data: Dict[str, Any],
    analysis: Dict[str, Any],
    insights: Dict[str, Any]
) -> None:
    """Store weather analysis results in the knowledge graph."""
    if not self.knowledge_graph:
        return

    # Create weather observation node
    observation_id = f"weather_{city.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"

    try:
        # Add weather observation
        await self.knowledge_graph.update_graph({
            observation_id: {
                "rdf:type": "WeatherObservation",
                "city": city,
                "temperature": weather_data["main"]["temp"],
                "humidity": weather_data["main"]["humidity"],
                "wind_speed": weather_data["wind"]["speed"],
                "description": weather_data["weather"][0]["description"],
                "timestamp": weather_data["dt"],
                "analysis": json.dumps(analysis),
                "insights": json.dumps(insights)
            }
        })

        # Link to city if it exists
        city_node = f"city:{city.lower().replace(' ', '_')}"
        await self.knowledge_graph.add_triple(
            observation_id,
            "observedIn",
            city_node
        )

        self.logger.info(f"Stored weather analysis for {city} in knowledge graph")

    except Exception as e:
        self.logger.error(f"Failed to store weather analysis: {e}")
        # Don't raise - KG storage failure shouldn't break the analysis

def _process_forecast_data(self, forecast_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process raw forecast data into daily summaries."""
    daily_forecasts = []

    # Group by day
    from collections import defaultdict
    daily_data = defaultdict(list)

    for item in forecast_data["list"]:
        dt = datetime.fromtimestamp(item["dt"])
        day_key = dt.strftime("%Y-%m-%d")
        daily_data[day_key].append(item)

    # Create daily summaries
    for day, items in daily_data.items():
        temps = [item["main"]["temp"] for item in items]
        humidities = [item["main"]["humidity"] for item in items]
        weather_conditions = [item["weather"][0]["main"] for item in items]

        daily_forecasts.append({
            "date": day,
            "temp_min": min(temps),
            "temp_max": max(temps),
            "temp_avg": sum(temps) / len(temps),
            "humidity_avg": sum(humidities) / len(humidities),
            "main_conditions": list(set(weather_conditions)),
            "precipitation_chance": self._calculate_precipitation_chance(items)
        })

    return daily_forecasts

def _calculate_precipitation_chance(self, forecast_items: List[Dict[str, Any]]) -> float:
    """Calculate precipitation chance from forecast items."""
    # Simple heuristic: if any item has precipitation, estimate chance
    precip_items = [item for item in forecast_items if "rain" in item or "snow" in item]

    if not precip_items:
        return 0.0

    # Base chance on number of precip items vs total items
    return min(len(precip_items) / len(forecast_items) * 100, 100.0)
```

## Step 5: Create the Agent File

Create the file `agents/domain/weather_analysis_agent.py`:

```python
# Complete implementation from above
# (Copy all the code from the previous sections)
```

## Step 6: Register and Test the Agent

### Add to Agent Registry

```python
# In agents/core/agent_registry.py or your initialization script
from agents.domain.weather_analysis_agent import WeatherAnalysisAgent

# Register the agent
weather_agent = WeatherAnalysisAgent("weather_analyzer", api_key="your-api-key")
await registry.register_agent(weather_agent)
```

### Test the Agent

```python
# Test script
import asyncio
from agents.core.message_types import AgentMessage
from datetime import datetime

async def test_weather_agent():
    agent = WeatherAnalysisAgent("test_weather_agent")

    # Test weather analysis
    message = AgentMessage(
        sender_id="test_user",
        recipient_id="test_weather_agent",
        content={"city": "London,UK"},
        message_type="analyze_weather",
        timestamp=datetime.now()
    )

    response = await agent.process_message(message)
    print("Response:", response.content)

if __name__ == "__main__":
    asyncio.run(test_weather_agent())
```

## Step 7: Advanced Features (Optional)

### Add Caching

```python
from functools import lru_cache
import asyncio

class WeatherAnalysisAgent(BaseAgent):
    # ... existing code ...

    def __init__(self, agent_id: str, api_key: Optional[str] = None):
        # ... existing code ...
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    @lru_cache(maxsize=100)
    async def _fetch_weather_data_cached(self, city: str) -> Dict[str, Any]:
        """Cached version of weather data fetching."""
        cache_key = f"weather:{city}"
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                return cached_data

        # Fetch fresh data
        data = await self._fetch_weather_data(city)
        self._cache[cache_key] = (data, datetime.now().timestamp())
        return data
```

### Add Error Recovery

```python
async def _handle_weather_analysis(self, message: AgentMessage) -> AgentMessage:
    """Handle weather analysis with retry logic."""
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            # ... existing logic ...
            return response
        except aiohttp.ClientError as e:
            if attempt == max_retries - 1:
                raise
            self.logger.warning(f"Weather API call failed (attempt {attempt + 1}), retrying...")
            await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
```

## Complete Example

Here's a complete working example:

```python
#!/usr/bin/env python3
"""
Weather Analysis Agent Example
Complete implementation of a custom agent for the Semant system.
"""

import os
import json
from typing import Dict, Any, List, Optional
from agents.core.base_agent import BaseAgent
from agents.core.message_types import AgentMessage
from loguru import logger
import asyncio
import aiohttp
from datetime import datetime

class WeatherAnalysisAgent(BaseAgent):
    """Agent for analyzing weather data and providing insights."""

    CAPABILITIES = {
        "WEATHER_ANALYSIS",
        "DATA_FETCHING",
        "PATTERN_RECOGNITION"
    }

    def __init__(self, agent_id: str, api_key: Optional[str] = None):
        super().__init__(agent_id, "weather_analysis")
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logger.bind(agent_id=agent_id)

    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        if not self.api_key:
            raise ValueError("Weather API key is required")
        self.logger.info("Weather Analysis Agent initialized")

    async def shutdown(self) -> None:
        """Clean shutdown."""
        if self.session:
            await self.session.close()
        await super().shutdown()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process messages."""
        if message.message_type == "analyze_weather":
            return await self._handle_weather_analysis(message)
        return await self._handle_unknown_message(message)

    async def _handle_weather_analysis(self, message: AgentMessage) -> AgentMessage:
        """Handle weather analysis."""
        city = message.content.get("city")
        if not city:
            raise ValueError("City parameter required")

        weather_data = await self._fetch_weather_data(city)
        analysis = await self._analyze_weather_patterns(weather_data)

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={
                "city": city,
                "temperature": weather_data["main"]["temp"],
                "analysis": analysis,
                "status": "success"
            },
            message_type="weather_analysis_response",
            timestamp=datetime.now()
        )

    async def _fetch_weather_data(self, city: str) -> Dict[str, Any]:
        """Fetch weather data."""
        async with self.session.get(
            f"{self.base_url}/weather",
            params={"q": city, "appid": self.api_key, "units": "metric"}
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def _analyze_weather_patterns(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze weather patterns."""
        temp = weather_data["main"]["temp"]
        analysis = {"recommendations": []}

        if temp > 30:
            analysis["recommendations"].append("Stay hydrated")
        elif temp < 0:
            analysis["recommendations"].append("Wear warm clothes")

        return analysis

    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"error": "Unknown message type", "status": "error"},
            message_type="error_response",
            timestamp=datetime.now()
        )

# Example usage
async def demo():
    agent = WeatherAnalysisAgent("weather_demo")
    await agent.initialize()

    message = AgentMessage(
        sender_id="user",
        recipient_id="weather_demo",
        content={"city": "New York"},
        message_type="analyze_weather",
        timestamp=datetime.now()
    )

    response = await agent.process_message(message)
    print("Weather Analysis Result:")
    print(json.dumps(response.content, indent=2))

    await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(demo())
```

## Summary

You've learned how to:

1. **Plan your agent** - Define purpose and capabilities
2. **Extend BaseAgent** - Inherit from the base class
3. **Implement message handlers** - Process different message types
4. **Add external integrations** - Call APIs and handle responses
5. **Store data** - Integrate with the knowledge graph
6. **Handle errors** - Add proper error handling and logging
7. **Test your agent** - Create test cases and verify functionality

## Next Steps

- **Add more capabilities** - Extend your agent with additional features
- **Improve error handling** - Add retry logic and better error messages
- **Add caching** - Implement intelligent caching for better performance
- **Create tests** - Write comprehensive unit tests
- **Document your agent** - Add detailed documentation and examples

Happy agent building! 🚀
