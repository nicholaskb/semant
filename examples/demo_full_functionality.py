"""
Example script: demo_full_functionality

Run from project root:
    python -m examples.demo_full_functionality

Or:
    PYTHONPATH=. python examples/demo_full_functionality.py
"""
import asyncio
from agents.core.ttl_validation_agent import TTLValidationAgent
from agents.core.remote_kg_agent import RemoteKGAgent
from agents.utils.email_integration import EmailIntegration
from demo_self_assembly import AgentRegistry, AgentMessage, BaseAgent


# ----------------------------------------------------------------------
# Simple Email Agent (simulation mode)
# ----------------------------------------------------------------------


class EmailAgent(BaseAgent):
    """Agent that sends a demo email using EmailIntegration. Runs in simulation
    mode (use_real_email=False) so the demo is safe to execute anywhere.
    Message format expected:

        {
            "to": "recipient@example.com",
            "subject": "...",
            "body": "..."
        }
    """

    def __init__(self, agent_id: str = "email_agent"):
        super().__init__(agent_id, "email")
        # Real email mode – will send via SMTP if credentials (.env or env vars) exist.
        self._mailer = EmailIntegration(use_real_email=True)

    async def initialize(self) -> None:
        await super().initialize()
        self.logger.info("Email Agent initialized (simulation mode)")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type != "email_request":
            return await self._handle_unknown_message(message)

        to_addr = message.content.get("to")
        subject = message.content.get("subject", "Demo Email")
        body = message.content.get("body", "Hello from EmailAgent demo")

        result = self._mailer.send_email(recipient_id=to_addr, subject=subject, body=body)

        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"mail_status": result},
            timestamp=message.timestamp,
            message_type="email_response",
        )

    # Minimal shim because the BaseAgent in demo_self_assembly lacks the
    # heavyweight process_message wrapper used in core agents.
    async def process_message(self, message: AgentMessage) -> AgentMessage:  # type: ignore[override]
        return await self._process_message_impl(message)


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
    
    email_agent = EmailAgent()

    # Register agents
    await registry.register_agent(ttl_validator, ["ttl_validation"])
    await registry.register_agent(remote_kg, ["remote_kg"])
    await registry.register_agent(email_agent, ["email"])
 
    # Initialize agents
    await ttl_validator.initialize()
    await remote_kg.initialize()
    await email_agent.initialize()
    
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

    # ------------------------------------------------------------------
    # Demo Email Sending (simulation)
    # ------------------------------------------------------------------
    print("\nEmail Agent Demo (simulation – no real email sent):")

    email_request = AgentMessage(
        sender="user",
        recipient="email_agent",
        content={
            # Send to primary plus CC address; EmailIntegration treats the
            # comma-separated string as the recipient list for SMTP.
            "to": "primary.recipient@example.com, nicholas.k.baro@gmail.com",
            "subject": "Demo email from multi-agent system (with CC)",
            "body": "This is a simulated email generated by EmailAgent."
        },
        timestamp=0.0,
        message_type="email_request",
    )

    email_response = await registry.route_message(email_request)
    print(email_response.content)

if __name__ == "__main__":
    asyncio.run(run_full_demo()) 