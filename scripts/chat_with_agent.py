import argparse
import asyncio

from agents.domain.diary_agent import DiaryAgent
from agents.domain.simple_agents import FinanceAgent, CoachingAgent, IntelligenceAgent, DeveloperAgent
from agents.core.base_agent import AgentMessage

AGENT_MAP = {
    "diary": DiaryAgent,
    "finance": FinanceAgent,
    "coaching": CoachingAgent,
    "intelligence": IntelligenceAgent,
    "developer": DeveloperAgent,
}

async def chat(agent):
    await agent.initialize()
    print(f"Chatting with {agent.agent_id}. Type 'quit' to exit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"quit", "exit"}:
            break

        if isinstance(agent, DiaryAgent):
            msg = AgentMessage(
                sender="user",
                recipient=agent.agent_id,
                content={"entry": user_input},
                timestamp=0.0,
                message_type="add_entry",
            )
            response = await agent.process_message(msg)
            print("Agent:", response.content.get("status"))
        else:
            msg = AgentMessage(
                sender="user",
                recipient=agent.agent_id,
                content={},
                timestamp=0.0,
                message_type="user_message",
            )
            response = await agent.process_message(msg)
            print("Agent:", response.content.get("response"))


def main():
    parser = argparse.ArgumentParser(description="Interact with a simple agent")
    parser.add_argument("agent", choices=AGENT_MAP.keys(), help="Agent to chat with")
    args = parser.parse_args()

    agent_cls = AGENT_MAP[args.agent]
    agent = agent_cls()
    asyncio.run(chat(agent))

if __name__ == "__main__":
    main()
