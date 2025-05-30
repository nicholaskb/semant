import asyncio
from agents.domain.vertex_email_agent import VertexEmailAgent
from agents.domain.judge_agent import JudgeAgent
from kg.models.graph_manager import KnowledgeGraphManager
from agents.core.base_agent import AgentMessage


async def main() -> None:
    kg = KnowledgeGraphManager()
    email_agent = VertexEmailAgent()
    judge = JudgeAgent(kg=kg)
    email_agent.knowledge_graph = kg
    judge.knowledge_graph = kg

    await email_agent.initialize()
    await judge.initialize()

    print(f"Initial triple count: {len(kg.graph)}")

    msg = AgentMessage(
        sender="demo",
        recipient=email_agent.agent_id,
        content={"recipient": "user@example.com", "subject": "Hello", "body": "Test"},
        timestamp=0.0,
        message_type="send_email",
    )
    await email_agent.process_message(msg)

    decision = await judge.evaluate_challenge("email sent")
    print(f"Judge decision: {decision}")

    print(f"Final triple count: {len(kg.graph)}")
    print("Diary entries:")
    for entry in judge.diary:
        print(entry)

if __name__ == "__main__":
    asyncio.run(main())
