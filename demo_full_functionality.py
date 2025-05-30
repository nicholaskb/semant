import asyncio
from agents.core.ttl_validation_agent import TTLValidationAgent
from agents.core.remote_kg_agent import RemoteKGAgent
from demo_self_assembly import AgentRegistry, AgentMessage

async def run_full_demo():
    # Create registry
    registry = AgentRegistry()
    
    # Create agents
    ttl_validator = TTLValidationAgent()
    # Using Wikidata's public SPARQL endpoint
    remote_kg = RemoteKGAgent(
        query_endpoint="https://query.wikidata.org/sparql",
        update_endpoint=None  # Wikidata doesn't allow updates
    )
    
    # Register agents
    await registry.register_agent(ttl_validator, ["ttl_validation"])
    await registry.register_agent(remote_kg, ["remote_kg"])
    
    # Initialize agents
    await ttl_validator.initialize()
    await remote_kg.initialize()
    
    # Demo TTL Validation
    print("\nTTL Validation Demo:")
    ttl_request = AgentMessage(
        sender="user",
        recipient="ttl_validation_agent",
        content={"file_path": "kg/schemas/test.ttl"},
        timestamp=0.0,
        message_type="ttl_validation_request"
    )
    ttl_response = await registry.route_message(ttl_request)
    print(ttl_response.content)
    
    # Demo Remote KG SPARQL Query
    print("\nRemote KG SPARQL Query Demo:")
    # Simple query to get 3 domestic cats from Wikidata
    sparql_query = """
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wikibase: <http://wikiba.se/ontology#>
    PREFIX bd: <http://www.bigdata.com/rdf#>
    
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label { bd:serviceParam wikibase:language 'en'. }
    }
    LIMIT 3
    """
    remote_kg_request = AgentMessage(
        sender="user",
        recipient="remote_kg_agent",
        content={"query": sparql_query},
        timestamp=0.0,
        message_type="sparql_query"
    )
    remote_kg_response = await registry.route_message(remote_kg_request)
    print(remote_kg_response.content)

if __name__ == "__main__":
    asyncio.run(run_full_demo()) 