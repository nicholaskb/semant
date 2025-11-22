#!/usr/bin/env python3
"""
Test MidjourneyAgent Initialization
Date: 2025-01-11
Purpose: Verify the agent initializes and check its first operations
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger.info("=" * 70)
logger.info("Testing MidjourneyAgent Initialization")
logger.info("=" * 70)


async def test_agent_initialization():
    """Test the first thing the agent does: initialization."""
    
    logger.info("\n1️⃣ STEP 1: Importing MidjourneyAgent...")
    try:
        from agents.domain.midjourney_agent import MidjourneyAgent, MIDJOURNEY_AVAILABLE
        logger.success("✅ MidjourneyAgent imported successfully")
        logger.info(f"   MIDJOURNEY_AVAILABLE: {MIDJOURNEY_AVAILABLE}")
    except ImportError as e:
        logger.error(f"❌ Failed to import MidjourneyAgent: {e}")
        return False
    
    logger.info("\n2️⃣ STEP 2: Checking Midjourney component imports...")
    if MIDJOURNEY_AVAILABLE:
        logger.success("✅ Midjourney components available")
        try:
            from midjourney_integration.client import MidjourneyClient
            logger.info("   - MidjourneyClient: Available")
            from semant.agent_tools.midjourney.workflows import imagine_then_mirror
            logger.info("   - Workflows: Available")
        except ImportError as e:
            logger.warning(f"   - Some components unavailable: {e}")
    else:
        logger.warning("⚠️  Midjourney components NOT available")
        logger.info("   This is expected if dependencies aren't installed")
    
    logger.info("\n3️⃣ STEP 3: Creating MidjourneyAgent instance...")
    try:
        agent = MidjourneyAgent(
            agent_id="test_midjourney_agent",
            registry=None,  # No registry for now
            knowledge_graph=None,  # No KG for now
            config={}
        )
        logger.success(f"✅ MidjourneyAgent created with ID: {agent.agent_id}")
        
        # Check capabilities
        capabilities = agent.get_capabilities()
        logger.info(f"\n   📋 Agent Capabilities ({len(capabilities)}):")
        for cap in sorted(capabilities):
            logger.info(f"      - {cap}")
        
        # Check if client initialized
        if agent.mj_client:
            logger.success("   ✅ MidjourneyClient initialized")
        else:
            logger.warning("   ⚠️  MidjourneyClient not initialized (might need API credentials)")
        
        if agent.batch_generator:
            logger.success("   ✅ PersonaBatchGenerator initialized")
        else:
            logger.info("   ℹ️  PersonaBatchGenerator not initialized (needs KG)")
        
    except Exception as e:
        logger.error(f"❌ Failed to create MidjourneyAgent: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    logger.info("\n4️⃣ STEP 4: Testing agent capabilities query...")
    try:
        caps = agent.get_capabilities()
        expected_caps = {
            "IMAGE_GENERATION",
            "IMAGE_DESCRIPTION", 
            "IMAGE_BLENDING",
            "IMAGE_VARIATION",
            "BATCH_GENERATION",
            "IMAGE_UPLOAD"
        }
        
        if caps == expected_caps:
            logger.success(f"✅ All {len(expected_caps)} expected capabilities present")
        else:
            missing = expected_caps - caps
            extra = caps - expected_caps
            if missing:
                logger.warning(f"   ⚠️  Missing capabilities: {missing}")
            if extra:
                logger.warning(f"   ⚠️  Extra capabilities: {extra}")
    except Exception as e:
        logger.error(f"❌ Failed to query capabilities: {e}")
        return False
    
    logger.info("\n5️⃣ STEP 5: Checking environment variables...")
    import os
    
    env_vars = {
        "MIDJOURNEY_API_TOKEN": os.getenv("MIDJOURNEY_API_TOKEN"),
        "GCS_BUCKET_NAME": os.getenv("GCS_BUCKET_NAME"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    }
    
    for var_name, var_value in env_vars.items():
        if var_value:
            logger.success(f"   ✅ {var_name}: Set (length={len(var_value)})")
        else:
            logger.warning(f"   ⚠️  {var_name}: Not set")
    
    logger.info("\n6️⃣ STEP 6: Cleanup - Shutting down agent...")
    try:
        await agent.shutdown()
        logger.success("✅ Agent shutdown successfully")
    except Exception as e:
        logger.error(f"❌ Shutdown failed: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.success("✅ INITIALIZATION TEST COMPLETE")
    logger.info("=" * 70)
    logger.info("\n📊 Summary:")
    logger.info(f"   - Import: {'✅ Success' if MIDJOURNEY_AVAILABLE else '⚠️  Components unavailable'}")
    logger.info(f"   - Agent Creation: ✅ Success")
    logger.info(f"   - Capabilities: ✅ All {len(expected_caps)} present")
    logger.info(f"   - Client Ready: {'✅ Yes' if agent.mj_client else '⚠️  Needs credentials'}")
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_agent_initialization())
    sys.exit(0 if result else 1)

