#!/usr/bin/env python3

import asyncio
import os
import logging
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent
from livekit.plugins import (
    cartesia,
    deepgram,
    silero,
    groq
)

load_dotenv(".env.local")
logger = logging.getLogger(__name__)

class HumanAgent(Agent):
    """Agent B - Simulates a human agent with different voice"""
    
    def __init__(self) -> None:
        instructions = """You are Agent B, a human specialist who has just joined to help a customer.

You should:
1. Greet the customer warmly
2. Acknowledge that you've been briefed on their situation
3. Ask how you can help them further
4. Provide excellent customer service

Be professional, helpful, and use a different speaking style than the AI agent."""

        super().__init__(instructions=instructions)
        self.conversation_history = ""

async def create_agent_b_session(room_url: str, token: str):
    """Create Agent B session and join the room"""
    try:
        logger.info(f"🤖 Agent B connecting to room with token: {token[:50]}...")
        
        human_agent = HumanAgent()
        
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=groq.LLM(model="llama-3.1-8b-instant"),
            tts=cartesia.TTS(
                model="sonic-english", 
                voice="156fb8d2-335b-4950-9cb3-a2d33befec77" 
            ),
            vad=silero.VAD.load(),
        )
        
        room = rtc.Room()
        await room.connect(room_url, token)
        
        await session.start(room=room, agent=human_agent)
        
        # Say hello to the customer
        await session.say(
            "Hello! I'm a specialist who's here to help you. I've been briefed on your situation. How can I assist you today?",
            allow_interruptions=True
        )
        
        logger.info("✅ Agent B is now active in the room")
        
        # Keep the session running - use a simple loop instead
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Agent B shutting down...")
        
    except Exception as e:
        logger.error(f"❌ Agent B connection failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python agent_b.py <room_url> <token>")
        sys.exit(1)
    
    room_url = sys.argv[1]
    token = sys.argv[2]
    
    asyncio.run(create_agent_b_session(room_url, token))
