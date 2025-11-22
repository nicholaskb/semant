#!/usr/bin/env python3
"""
llm_email_conversation_demo.py
================================
Demonstrates an end-to-end conversation between **two** Vertex-powered LLM
agents that communicate **only via email** using the existing helpers in this
repo.

• Agent A – VertexEmailAgent + EmailIntegration (SMTP/Gmail API)
• Agent B – VertexEmailAgent + EmailIntegration

How it works
------------
1. Agent A sends an initial email to Agent B.
2. Agents take turns reading / replying to the latest message in the thread.
3. The demo runs for `N_TURNS` exchanges (default = 3 per side).

Prerequisites
-------------
• OAuth Gmail credentials set up (credentials/credentials.json + token.pickle)
• Environment variables EMAIL_SENDER / EMAIL_PASSWORD **or** the Gmail API token
  – whichever path your EmailIntegration uses.
• Working Vertex SDK environment variables (GOOGLE_APPLICATION_CREDENTIALS etc.)

Usage
-----
```
python examples/llm_email_conversation_demo.py \
       --agent-a agent.a.demo@gmail.com \
       --agent-b agent.b.demo@gmail.com \
       --turns 3
```
If you omit the flags the script reads `AGENT_A_EMAIL` / `AGENT_B_EMAIL` env
vars or finally falls back to the same inbox for both agents.
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure project root is on path so imports resolve when run directly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.domain.vertex_email_agent import VertexEmailAgent
from email_utils.send_gmail_test import (
    get_gmail_service,
    send_email,
    list_message_ids,
    get_message_body,
)

N_TURNS_DEFAULT = 3  # messages *per agent*
SLEEP_BETWEEN_EMAILS = 15  # seconds – allows Gmail to deliver
THREAD_SUBJECT = "🤖 LLM ↔ LLM email demo"
CC_EMAIL = "nicholas.k.baro@gmail.com"


async def generate_and_send(
    llm_agent: VertexEmailAgent,
    send_func,
    to_addr: str,
    instruction: str,
):
    """Ask LLM to craft a reply based on `instruction` and send it."""
    content = await llm_agent.enhance_email_content(instruction)
    # primary send
    send_func(to_addr, content)
    # CC copy
    if CC_EMAIL and CC_EMAIL != to_addr:
        send_email(
            service=None, # This will be updated in run_conversation
            recipient_id=CC_EMAIL,
            subject=f"[CC] {THREAD_SUBJECT}",
            body=f"(CC of message sent to {to_addr})\n\n" + content,
        )
    print(f"📧 Email sent to {to_addr} via Gmail API (cc {CC_EMAIL})\n---\n{content[:200]}...\n---")


async def run_conversation(agent_a_email: str, agent_b_email: str, turns: int):
    print("🚀 Initialising agents …")
    # Instantiate LLM agents
    agent_a = VertexEmailAgent(); await agent_a.initialize()
    agent_b = VertexEmailAgent(); await agent_b.initialize()

    # Build Gmail API service once for both agents
    service = get_gmail_service()

    def api_send(to_addr: str, body: str):
        """Send email (and CC) via Gmail API."""
        # Primary
        send_email(service, to_addr, THREAD_SUBJECT, body)
        # CC copy if needed
        if CC_EMAIL and CC_EMAIL != to_addr:
            send_email(
                service,
                CC_EMAIL,
                f"[CC] {THREAD_SUBJECT}",
                f"(CC of message sent to {to_addr})\n\n{body}"
            )

    # 1. Kick-off message from A to B
    print("\n🎯 Agent A kick-off → Agent B")
    # Kick-off via Gmail API
    kick_body = "Hello Agent B, please draft a short poem about collaboration."
    api_send(agent_b_email, kick_body)

    # Alternate replies
    for i in range(turns):
        print(f"\n🔄 Turn {i + 1} – Agent B replying …")
        await asyncio.sleep(SLEEP_BETWEEN_EMAILS)
        await generate_and_send(
            agent_b,
            api_send,
            to_addr=agent_a_email,
            instruction="Reply concisely to the previous message. Sign as ‘Agent B’.",
        )

        print(f"\n🔄 Turn {i + 1} – Agent A replying …")
        await asyncio.sleep(SLEEP_BETWEEN_EMAILS)
        await generate_and_send(
            agent_a,
            api_send,
            to_addr=agent_b_email,
            instruction="Reply to the last message. Keep the thread going. Sign as ‘Agent A’.",
        )

    print("\n🏁 Conversation complete – check both inboxes!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM-to-LLM email conversation demo")
    parser.add_argument("--agent-a", dest="agent_a", help="Email address for Agent A")
    parser.add_argument("--agent-b", dest="agent_b", help="Email address for Agent B")
    parser.add_argument("--turns", type=int, default=N_TURNS_DEFAULT, help="Number of reply turns per agent")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    a_email = args.agent_a or os.getenv("AGENT_A_EMAIL") or os.getenv("EMAIL_SENDER")
    b_email = args.agent_b or os.getenv("AGENT_B_EMAIL") or a_email  # default to same inbox

    if not a_email or not b_email:
        print("❌ Must provide --agent-a and --agent-b or set AGENT_A_EMAIL / AGENT_B_EMAIL env vars")
        sys.exit(1)

    print(f"📧 Agent A: {a_email}\n📧 Agent B: {b_email}\n")
    asyncio.run(run_conversation(a_email, b_email, args.turns)) 