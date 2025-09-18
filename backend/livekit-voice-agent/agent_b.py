#!/usr/bin/env python3

import asyncio
import logging
import os
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, WorkerOptions, cli
from livekit.plugins import cartesia, deepgram, silero, groq

load_dotenv(".env.local")
logger = logging.getLogger(__name__)

class SpecialistAgent(Agent):
    """Agent B - A human specialist with different voice"""
    
    def __init__(self, conversation_history: str = "") -> None:
        # Create context-aware instructions based on conversation history
        if conversation_history.strip():
            instructions = f"""You are Sarah, a technical support specialist who has just joined this call.

You are professional, knowledgeable, and helpful. You have been briefed on the previous conversation:

{conversation_history}

Based on this context, greet the customer naturally and continue helping them with their specific needs. Reference the previous conversation appropriately to show continuity."""
        else:
            instructions = """You are Sarah, a technical support specialist who has just joined this call.

You are professional, knowledgeable, and helpful. The customer has already been told you're a specialist, so greet them naturally and continue helping them."""

        super().__init__(instructions=instructions)
        self.conversation_history = conversation_history

async def entrypoint(ctx: JobContext):
    """Agent B entrypoint with conversation history context"""
    logger.info("🤖 Agent B (Sarah) starting up...")
    
    # Get conversation history from environment variable
    conversation_history = os.getenv("CONVERSATION_HISTORY", "")
    logger.info(f"📝 Agent B received conversation history: {len(conversation_history)} characters")
    
    # Create the specialist agent with conversation context
    specialist_agent = SpecialistAgent(conversation_history)
    
    # Create agent session with different voice (Calm Lady)
    session = AgentSession(
        stt=deepgram.STT(model="nova-2", language="en"),
        llm=groq.LLM(model="llama-3.1-8b-instant"),
        tts=cartesia.TTS(
            model="sonic-english",
            voice="156fb8d2-335b-4950-9cb3-a2d33befec77"  # Calm Lady voice
        ),
        vad=silero.VAD.load(),
    )
    
    # Start the session
    await session.start(room=ctx.room, agent=specialist_agent)
    
    # Create context-aware greeting based on conversation history
    if conversation_history.strip():
        # Extract key points from conversation for personalized greeting
        greeting = "Hello! This is Sarah, a technical support specialist. I've been briefed on your conversation with my colleague and I'm here to continue helping you. Let me pick up where we left off."
    else:
        greeting = "Hello! This is Sarah, a technical support specialist. I've been briefed on your case and I'm here to help you. What can I assist you with?"
    
    await session.say(greeting, allow_interruptions=True)
    
    logger.info("✅ Agent B (Sarah) is now active and ready to help")

if __name__ == "__main__":
    # Use standard LiveKit CLI - no custom token handling
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
