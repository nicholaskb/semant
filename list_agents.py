#!/usr/bin/env python3
"""
Agent List Generator
Lists all available agents and their capabilities from the repository.
Can optionally query the knowledge graph for registered agents.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import importlib.util
import inspect

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.core.base_agent import BaseAgent
from agents.core.capability_types import CapabilityType, Capability
from agents.core.agent_registry import AgentRegistry
from agents.core.agent_factory import AgentFactory
from loguru import logger

# Suppress verbose logging
logger.remove()
logger.add(sys.stderr, level="WARNING")


async def discover_agent_classes() -> Dict[str, Dict[str, Any]]:
    """Discover all agent classes in the repository."""
    agents_info = {}
    agents_dir = Path(__file__).parent / "agents"
    
    # Search in core and domain directories
    for subdir in ["core", "domain"]:
        subdir_path = agents_dir / subdir
        if not subdir_path.exists():
            continue
            
        for file_path in subdir_path.glob("*.py"):
            if file_path.name.startswith("__") or file_path.name.startswith("test_"):
                continue
                
            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(
                    file_path.stem, file_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find agent classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseAgent) and 
                            obj != BaseAgent):
                            
                            # Get class info
                            doc = inspect.getdoc(obj) or "No description"
                            sig = inspect.signature(obj.__init__)
                            
                            agents_info[name] = {
                                "class": obj,
                                "module": f"{subdir}.{file_path.stem}",
                                "file": str(file_path.relative_to(Path(__file__).parent)),
                                "doc": doc.split("\n")[0] if doc else "No description",
                                "full_doc": doc,
                                "init_params": list(sig.parameters.keys())[1:],  # Skip 'self'
                            }
            except Exception as e:
                logger.debug(f"Error loading {file_path}: {e}")
                continue
                
    return agents_info


async def get_agent_capabilities(agent_class, agent_id: str = "temp") -> Set[Capability]:
    """Get capabilities for an agent class."""
    try:
        # Try to instantiate with minimal params
        sig = inspect.signature(agent_class.__init__)
        params = sig.parameters
        
        # Check if agent_id is required
        kwargs = {}
        if "agent_id" in params:
            kwargs["agent_id"] = agent_id
        elif "registry" in params:
            # Some agents need registry
            registry = AgentRegistry(disable_auto_discovery=True)
            await registry.initialize()
            kwargs["registry"] = registry
        
        # Try to create agent
        agent = agent_class(**kwargs)
        await agent.initialize()
        capabilities = await agent.get_capabilities()
        
        # Cleanup
        if hasattr(agent, "cleanup"):
            await agent.cleanup()
        if "registry" in kwargs:
            await registry.cleanup()
            
        return capabilities
    except Exception as e:
        logger.debug(f"Could not get capabilities for {agent_class.__name__}: {e}")
        return set()


async def query_knowledge_graph_for_agents(kg_manager=None) -> Dict[str, Any]:
    """Query knowledge graph for registered agents."""
    kg_agents = {}
    
    if kg_manager is None:
        try:
            from kg.kg_manager import KnowledgeGraphManager
            kg_manager = KnowledgeGraphManager()
            await kg_manager.initialize()
        except Exception as e:
            logger.debug(f"Could not initialize KG: {e}")
            return kg_agents
    
    try:
        # SPARQL query for agents
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX sem: <http://example.org/semant#>
        
        SELECT ?agent ?capability ?type
        WHERE {
            ?agent rdf:type sem:Agent .
            OPTIONAL {
                ?agent sem:hasCapability ?capability .
                ?capability rdf:type ?type .
            }
        }
        """
        
        results = await kg_manager.query_graph(query)
        
        for row in results:
            agent_uri = str(row.get("agent", ""))
            capability = str(row.get("capability", ""))
            if agent_uri:
                if agent_uri not in kg_agents:
                    kg_agents[agent_uri] = {"capabilities": []}
                if capability:
                    kg_agents[agent_uri]["capabilities"].append(capability)
                    
    except Exception as e:
        logger.debug(f"KG query failed: {e}")
    finally:
        if kg_manager:
            try:
                await kg_manager.shutdown()
            except:
                pass
                
    return kg_agents


def format_agent_list(agents_info: Dict[str, Dict[str, Any]], 
                     capabilities_map: Dict[str, Set[Capability]],
                     kg_agents: Dict[str, Any] = None) -> str:
    """Format the agent list as a readable string."""
    output = []
    output.append("=" * 80)
    output.append("AGENT CAPABILITY LIST")
    output.append("=" * 80)
    output.append("")
    
    # Group by directory
    core_agents = {}
    domain_agents = {}
    
    for name, info in agents_info.items():
        if info["module"].startswith("core"):
            core_agents[name] = info
        else:
            domain_agents[name] = info
    
    # Core Agents
    if core_agents:
        output.append("CORE AGENTS")
        output.append("-" * 80)
        for name in sorted(core_agents.keys()):
            info = core_agents[name]
            output.append(f"\n{name}")
            output.append(f"  Module: {info['module']}")
            output.append(f"  File: {info['file']}")
            output.append(f"  Description: {info['doc']}")
            
            if info['init_params']:
                output.append(f"  Init Params: {', '.join(info['init_params'])}")
            
            caps = capabilities_map.get(name, set())
            if caps:
                cap_list = sorted([str(c) for c in caps])
                output.append(f"  Capabilities ({len(caps)}):")
                for cap in cap_list:
                    output.append(f"    - {cap}")
            else:
                output.append("  Capabilities: (unknown)")
            output.append("")
    
    # Domain Agents
    if domain_agents:
        output.append("\n" + "=" * 80)
        output.append("DOMAIN AGENTS")
        output.append("-" * 80)
        for name in sorted(domain_agents.keys()):
            info = domain_agents[name]
            output.append(f"\n{name}")
            output.append(f"  Module: {info['module']}")
            output.append(f"  File: {info['file']}")
            output.append(f"  Description: {info['doc']}")
            
            if info['init_params']:
                output.append(f"  Init Params: {', '.join(info['init_params'])}")
            
            caps = capabilities_map.get(name, set())
            if caps:
                cap_list = sorted([str(c) for c in caps])
                output.append(f"  Capabilities ({len(caps)}):")
                for cap in cap_list:
                    output.append(f"    - {cap}")
            else:
                output.append("  Capabilities: (unknown)")
            output.append("")
    
    # Summary
    output.append("\n" + "=" * 80)
    output.append("SUMMARY")
    output.append("-" * 80)
    output.append(f"Total Agents Found: {len(agents_info)}")
    output.append(f"  Core Agents: {len(core_agents)}")
    output.append(f"  Domain Agents: {len(domain_agents)}")
    
    # Capability summary
    all_caps = set()
    for caps in capabilities_map.values():
        all_caps.update(caps)
    
    output.append(f"\nTotal Unique Capabilities: {len(all_caps)}")
    if all_caps:
        output.append("Capability Types:")
        for cap_type in sorted(set(c.type.value if isinstance(c.type, CapabilityType) else str(c.type) 
                                   for c in all_caps)):
            output.append(f"  - {cap_type}")
    
    # Knowledge Graph info
    if kg_agents:
        output.append(f"\nAgents in Knowledge Graph: {len(kg_agents)}")
    
    output.append("\n" + "=" * 80)
    
    return "\n".join(output)


async def main():
    """Main function."""
    print("Discovering agents...")
    agents_info = await discover_agent_classes()
    
    print(f"Found {len(agents_info)} agent classes")
    print("Getting capabilities...")
    
    capabilities_map = {}
    for name, info in agents_info.items():
        try:
            caps = await get_agent_capabilities(info["class"], f"{name.lower()}_test")
            capabilities_map[name] = caps
        except Exception as e:
            logger.debug(f"Could not get capabilities for {name}: {e}")
            capabilities_map[name] = set()
    
    print("Querying knowledge graph (if available)...")
    kg_agents = await query_knowledge_graph_for_agents()
    
    # Format and print
    output = format_agent_list(agents_info, capabilities_map, kg_agents)
    print("\n" + output)
    
    # Also save to file
    output_file = Path(__file__).parent / "agent_list.txt"
    output_file.write_text(output)
    print(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
