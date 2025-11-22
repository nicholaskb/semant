# Planner Agent Troubleshooting Guide

## Overview
The Planner agent is responsible for refining and generating prompts for Midjourney image generation. This guide explains how to verify it's working and fix common issues.

## Quick Status Check

### Method 1: API Endpoint
```bash
curl -X GET http://localhost:8000/api/planner-status | python3 -m json.tool
```

### Method 2: Test Script
```bash
python3 test_planner_refinement.py
```

## Understanding the Status Response

A healthy planner status looks like:
```json
{
    "imports_ok": true,
    "planner_available": true,
    "planner_type": "PlannerAgent",
    "registry_available": true,
    "registry_agents": [
        "prompt_refiner",
        "planner",
        "logo_analyzer",
        "aesthetics_analyzer",
        "color_palette_analyzer",
        "composition_analyzer",
        "synthesis_agent",
        "critic_agent",
        "judge_agent"
    ],
    "planner_functional": "process_message method exists"
}
```

## Common Reasons for Planner Unavailability

### 1. Import Failures (`imports_ok: false`)

**Symptoms:**
- Status shows `imports_ok: false`
- Server logs show: `Multi-agent refinement modules not loaded`

**Causes:**
- Missing `agents/` directory
- Python import path issues
- Missing dependencies in agent modules
- Syntax errors in agent files

**Fix:**
```bash
# Verify imports manually
python3 -c "from agents.domain.planner_agent import PlannerAgent"
python3 -c "from agents.core.agent_registry import AgentRegistry"

# Check for missing dependencies
pip install -r requirements.txt

# Ensure agents directory is in Python path
export PYTHONPATH="${PYTHONPATH}:/Users/nicholasbaro/Python/semant"
```

### 2. Initialization Failures (`planner_available: false`)

**Symptoms:**
- Status shows `imports_ok: true` but `planner_available: false`
- Server logs show: `Multi-agent refinement not available: [error]`

**Causes:**
- Agent registry initialization failed
- Planner agent registration failed
- Database/KG connection issues
- Memory or resource constraints

**Fix:**
```bash
# Check server startup logs
grep "Multi-agent" server.log

# Restart the server with verbose logging
TASKMASTER_LOG_LEVEL=DEBUG python3 main.py

# Clear any corrupted state
rm -rf __pycache__
rm -rf agents/__pycache__
rm -rf agents/*/__pycache__
```

### 3. Mock Object Issues

**Symptoms:**
- Status shows warning: `"Planner is a Mock object - not functional"`
- Runtime errors: `object MagicMock can't be used in 'await' expression`

**Causes:**
- Test code interfering with production
- Incomplete cleanup after tests
- Import order issues

**Fix:**
```bash
# Ensure tests aren't imported in production
grep -r "from unittest.mock import" agents/
grep -r "MagicMock\|AsyncMock" main.py

# Restart server cleanly
pkill -f "python.*main.py"
python3 main.py
```

## How the Planner Works

### In Generate Themed Set:

1. **Base Prompt Generation**: `_generate_theme_aware_prompt(theme)`
   - Creates structured prompts based on theme (Marvel, fantasy, etc.)
   - Includes technical details (lighting, composition, etc.)

2. **Planner Refinement**: If planner is available
   - Each base prompt is sent to the Planner
   - Planner enhances with descriptive details
   - Falls back to base prompt if refinement fails

3. **Submission**: Refined prompts are sent to Midjourney with reference images

### Flow Diagram:
```
Theme Input → Base Generator → [Planner Refinement] → Midjourney API
                                    ↓ (if unavailable)
                                 Use Base Prompt
```

## Testing the Planner

### Test 1: Direct Refinement
```python
import requests

response = requests.post(
    "http://localhost:8000/api/midjourney/refine-prompt",
    json={"prompt": "superhero portrait"}
)
print(response.json())
```

### Test 2: Verify in Logs
When using Generate Themed Set, look for:
```
INFO: Refining prompt via Planner: [base prompt]
INFO: Refined prompt: [enhanced prompt]
```

## Environment Variables

The Planner doesn't require special environment variables, but ensure:
```bash
# In .env file
OPENAI_API_KEY=your_key_here  # For prompt_refiner agent
```

## When Planner is Unavailable

The system gracefully degrades:
- Base prompts are still theme-aware and structured
- Quality is good but less descriptive
- All features continue to work

## Forcing Planner Availability

If the planner should be available but isn't:

1. **Check all imports:**
```bash
find agents -name "*.py" -exec python3 -m py_compile {} \;
```

2. **Verify agent files exist:**
```bash
ls -la agents/domain/planner_agent.py
ls -la agents/core/agent_registry.py
```

3. **Test initialization directly:**
```python
import asyncio
from agents.core.agent_registry import AgentRegistry
from agents.domain.planner_agent import PlannerAgent

async def test():
    registry = AgentRegistry(disable_auto_discovery=True)
    await registry.initialize()
    planner = PlannerAgent("test_planner", registry)
    await registry.register_agent(planner)
    print("Success!")

asyncio.run(test())
```

## Performance Impact

- **With Planner**: ~200-500ms additional latency per prompt
- **Without Planner**: No additional latency
- **Memory**: ~50MB for agent registry and planner

## Monitoring

Watch for these log messages:
- ✅ `Multi-agent refinement planner initialized`
- ⚠️ `Multi-agent refinement not available: [reason]`
- ⚠️ `Multi-agent refinement modules not loaded: [error]`
- ❌ `Planner initialization returned a Mock object`

## Support

If issues persist after trying these solutions:
1. Check the scratch_space directory for recent debugging notes
2. Review main.py lines 229-345 (agent initialization)
3. Verify agents/domain/planner_agent.py exists and is valid Python
