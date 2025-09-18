from dotenv import load_dotenv
import aiohttp
import asyncio
import logging
import os

from livekit import agents, api, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, llm, function_tool, RunContext
from livekit.plugins import (
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
    groq
)

from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local")

logger = logging.getLogger(__name__)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY") 
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Backend API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# For now, we'll simulate transfers without SIP
ENABLE_SIP_TRANSFER = False

class TransferAgent(Agent):
    """Agent that handles the consultation with supervisor during warm transfer"""
    
    def __init__(self, conversation_history: str = "") -> None:
        instructions = f"""You are a transfer agent helping with a warm transfer process.
        
Your role is to:
1. Summarize the previous conversation to the supervisor
2. Provide context about why the transfer was requested
3. Answer any questions the supervisor has
4. Facilitate the handoff to the supervisor

Previous conversation history:
{conversation_history}

Be concise but thorough in your summary. Help the supervisor understand the customer's needs quickly."""

        super().__init__(instructions=instructions)
        self.conversation_history = conversation_history

class WarmTransferManager:
    """Manages the warm transfer process following LiveKit's recommended pattern"""
    
    def __init__(self, ctx: agents.JobContext):
        self.ctx = ctx
        self.api_client = ctx.api if hasattr(ctx, 'api') else None
        
    async def initiate_warm_transfer(self, customer_session: AgentSession, conversation_history: str):
        """
        Initiate warm transfer using your backend API
        """
        try:
            logger.info("🔄 Starting warm transfer process with backend API")
            
            # Tell customer we're connecting them
            await customer_session.say(
                "I understand you need to speak with a specialist. Let me connect you now. Please hold for just a moment while I find the right person to help you.",
                allow_interruptions=False
            )
            
            # Call your backend API to initiate the transfer
            room_id = self.ctx.room.name
            transfer_result = await self._call_backend_transfer_api(room_id, conversation_history)
            
            if transfer_result and transfer_result.get("transfer_id"):
                transfer_id = transfer_result.get("transfer_id")
                logger.info(f"✅ Transfer initiated via backend API: {transfer_id}")
                
                # Simulate brief hold time
                await asyncio.sleep(2)
                
                # Complete the transfer
                complete_result = await self._complete_backend_transfer(transfer_id)
                
                if complete_result and complete_result.get("success"):
                    await customer_session.say(
                        "Perfect! I've successfully connected you with one of our specialists. They have been briefed on your situation and are ready to help you. Thank you for your patience!",
                        allow_interruptions=False
                    )
                    logger.info(f"✅ Transfer completed successfully: {transfer_id}")
                    
                    # Start Agent B if we have the token
                    agent_b_token = complete_result.get("agent_b_token")
                    livekit_url = complete_result.get("livekit_url")
                    
                    if agent_b_token and livekit_url:
                        logger.info("🚀 Starting real Agent B to join the room...")
                        await self._start_agent_b(livekit_url, agent_b_token, conversation_history)
                        
                        # Give Agent B time to connect and introduce themselves
                        await asyncio.sleep(5)
                        
                        # Now disconnect this AI agent to complete handoff
                        logger.info("🔄 AI Agent disconnecting to complete handoff...")
                        await self._disconnect_ai_agent(customer_session)
                    else:
                        logger.error("❌ No Agent B token received, cannot start real agent")
                        # Fallback to announcing the transfer
                        await customer_session.say(
                            "I've initiated your transfer to a specialist. They should be connecting with you shortly!",
                            allow_interruptions=False
                        )
                    
                    logger.info("✅ Real agent handoff process completed")
                    
                    return True
                else:
                    logger.error(f"❌ Failed to complete transfer: {transfer_id}")
                    # Don't fail the whole transfer if completion fails
                    await customer_session.say(
                        "I've initiated your transfer to a specialist. They should be connecting with you shortly!",
                        allow_interruptions=False
                    )
                    return True
            else:
                logger.error("❌ Failed to initiate transfer via backend API")
                raise Exception("Transfer initiation failed")
                
        except Exception as e:
            logger.error(f"❌ Warm transfer failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Restore normal call state
            try:
                await customer_session.say(
                    "I apologize, but I'm having trouble connecting you to a specialist right now. Let me continue helping you directly. How can I assist you?",
                    allow_interruptions=False
                )
            except:
                pass
            return False
    
    async def _call_backend_transfer_api(self, room_id: str, conversation_history: str):
        """Call your backend API to initiate transfer"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get the actual participant identities from the room
                caller_identity = None
                agent_identity = None
                
                if hasattr(self.ctx, 'room'):
                    # Get local participant (this agent)
                    if hasattr(self.ctx.room, 'local_participant'):
                        agent_identity = self.ctx.room.local_participant.identity
                    
                    # Get remote participants (the caller)
                    if hasattr(self.ctx.room, 'remote_participants'):
                        for participant in self.ctx.room.remote_participants.values():
                            caller_identity = participant.identity
                            break  # Take the first remote participant as the caller
                
                # Fallbacks if we can't get the identities
                if not caller_identity:
                    caller_identity = f"user_{room_id.split('_')[-1]}" if '_' in room_id else "caller"
                if not agent_identity:
                    agent_identity = "ai_agent"
                
                logger.info(f"🔍 Using identities - Caller: {caller_identity}, Agent: {agent_identity}")
                
                transfer_data = {
                    "room_id": room_id,
                    "target_agent_id": "agent_general",
                    "caller_identity": caller_identity,
                    "agent_a_identity": agent_identity,
                    "call_summary": f"Customer requested transfer. Conversation: {conversation_history[:500]}...",
                    "conversation_history": conversation_history,  # Full conversation history
                    "metadata": {
                        "initiated_by": "ai_agent",
                        "reason": "customer_request",
                        "conversation_length": len(conversation_history)
                    }
                }
                
                logger.info(f"🔗 Calling backend API: {API_BASE_URL}/api/transfers/initiate")
                logger.info(f"📤 Transfer data: {transfer_data}")
                
                async with session.post(
                    f"{API_BASE_URL}/api/transfers/initiate",
                    json=transfer_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Backend API response: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Backend API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error calling backend API: {e}")
            return None
    
    async def _complete_backend_transfer(self, transfer_id: str):
        """Complete the transfer via backend API"""
        try:
            async with aiohttp.ClientSession() as session:
                logger.info(f"🔗 Completing transfer: {API_BASE_URL}/api/transfers/complete/{transfer_id}")
                
                async with session.post(
                    f"{API_BASE_URL}/api/transfers/complete/{transfer_id}",
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Transfer completion response: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Transfer completion error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error completing transfer: {e}")
            return None
    
    async def _start_agent_b(self, livekit_url: str, agent_b_token: str, conversation_history: str = ""):
        """Start Agent B worker using standard LiveKit CLI"""
        try:
            import subprocess
            import os
            import asyncio
            
            # Get the path to agent_b.py
            agent_b_path = os.path.join(os.path.dirname(__file__), "agent_b.py")
            
            # Start Agent B worker using standard LiveKit CLI
            env = os.environ.copy()
            env["LIVEKIT_URL"] = livekit_url
            env["LIVEKIT_API_KEY"] = os.getenv("LIVEKIT_API_KEY")
            env["LIVEKIT_API_SECRET"] = os.getenv("LIVEKIT_API_SECRET")
            
            # Pass conversation history as environment variable
            logger.info(f"📝 Passing conversation history to Agent B: {len(conversation_history)} characters")
            logger.info(f"🗣️ Conversation content: {conversation_history[:200]}...")
            env["CONVERSATION_HISTORY"] = conversation_history
            
            # Use the standard LiveKit agent CLI - connect to specific room
            process = subprocess.Popen([
                "uv", "run", "python", agent_b_path, 
                "connect", 
                "--room", self.ctx.room.name
            ], 
            cwd=os.path.dirname(__file__),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
            )
            
            logger.info(f"🚀 Agent B worker started with PID: {process.pid}")
            logger.info(f"🔗 Agent B connecting to room: {self.ctx.room.name}")
            
            # Start a background task to monitor Agent B output
            asyncio.create_task(self._monitor_agent_b_output(process))
            
        except Exception as e:
            logger.error(f"❌ Error starting Agent B worker: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _monitor_agent_b_output(self, process):
        """Monitor Agent B subprocess output"""
        try:
            import asyncio
            
            async def read_stream(stream, prefix):
                while True:
                    line = await asyncio.to_thread(stream.readline)
                    if not line:
                        break
                    logger.info(f"🤖 Agent B {prefix}: {line.strip()}")
            
            # Monitor both stdout and stderr
            await asyncio.gather(
                read_stream(process.stdout, "STDOUT"),
                read_stream(process.stderr, "STDERR"),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error monitoring Agent B output: {e}")
    
    async def _disconnect_ai_agent(self, customer_session: AgentSession):
        """Disconnect the AI agent to complete the handoff"""
        try:
            logger.info("👋 AI Agent saying goodbye and disconnecting...")
            
            # Disconnect from the room properly
            if hasattr(self.ctx, 'room') and hasattr(self.ctx.room, 'disconnect'):
                await self.ctx.room.disconnect()
                logger.info("✅ AI Agent disconnected from room")
            elif hasattr(customer_session, 'aclose'):
                await customer_session.aclose()
                logger.info("✅ AI Agent session closed")
            elif hasattr(customer_session, 'close'):
                await customer_session.close()
                logger.info("✅ AI Agent session closed")
            else:
                logger.warning("⚠️ No close method found, agent will disconnect naturally")
            
            # The human agent (Agent B) should now join using the token from the backend
            logger.info("✅ AI Agent disconnected. Human agent should now join the room.")
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting AI agent: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")


async def handle_transfer_request(room_id: str, caller_identity: str, agent_identity: str, user_message: str):
    """
    Handle transfer requests by analyzing user message and initiating transfer
    """
    try:
        # Detect transfer keywords and intent
        transfer_keywords = [
            "transfer", "connect", "speak", "talk", "human", "agent", 
            "technical", "billing", "supervisor", "manager", "specialist",
            "help", "support", "escalate", "another", "different", "someone else"
        ]
        
        # More specific transfer phrases
        transfer_phrases = [
            "speak with", "talk to", "connect me", "transfer me", "another agent",
            "human agent", "different agent", "someone else", "escalate", 
            "supervisor", "manager", "specialist", "technical support"
        ]
        
        user_lower = user_message.lower()
        logger.info(f"Checking transfer for message: '{user_message}'")
        
        # Check if user is requesting a transfer (keywords OR phrases)
        keyword_match = any(keyword in user_lower for keyword in transfer_keywords)
        phrase_match = any(phrase in user_lower for phrase in transfer_phrases)
        
        logger.info(f"Keyword match: {keyword_match}, Phrase match: {phrase_match}")
        
        if keyword_match or phrase_match:
            # Determine agent type based on keywords
            if any(word in user_lower for word in ["technical", "tech", "login", "password", "system"]):
                target_agent_id = "agent_tech"
                agent_type = "technical support"
            elif any(word in user_lower for word in ["billing", "payment", "invoice", "charge"]):
                target_agent_id = "agent_billing"
                agent_type = "billing"
            elif any(word in user_lower for word in ["supervisor", "manager", "escalate", "complaint"]):
                target_agent_id = "agent_supervisor"
                agent_type = "supervisor"
            else:
                target_agent_id = "agent_general"
                agent_type = "specialist"
            
            # Initiate the warm transfer
            transfer_result = await initiate_warm_transfer(
                room_id=room_id,
                caller_identity=caller_identity,
                agent_a_identity=agent_identity,
                target_agent_id=target_agent_id,
                call_summary=f"Customer requested transfer: {user_message}"
            )
            
            if transfer_result:
                # Auto-complete the transfer after a brief moment
                await asyncio.sleep(2)
                
                complete_result = await complete_warm_transfer(transfer_result["transfer_id"])
                
                if complete_result:
                    return f"I understand you'd like to speak with {agent_type}. I'm transferring you now. Please hold while I connect you."
                else:
                    return f"I'm working on connecting you to {agent_type}. Please hold for just a moment."
            else:
                return f"I'd be happy to connect you with {agent_type}, but I'm having some technical difficulties. Let me see how I can help you directly in the meantime."
        
        return None  # No transfer needed
        
    except Exception as e:
        logger.error(f"Error handling transfer request: {e}")
        return None


class SupportAgent(Agent):
    """Main customer support agent that can initiate warm transfers"""
    
    def __init__(self, ctx: agents.JobContext) -> None:
        instructions = """You are a helpful voice AI assistant for customer support.

IMPORTANT: When customers ask to be transferred, connected to another agent, or need specialized help, you MUST call the transfer_to_specialist function immediately.

Common transfer requests include:
- "Can I speak to a human agent?"
- "Transfer me to technical support" 
- "I need to talk to a supervisor"
- "Connect me to billing"
- "I need specialist help"
- "Please let me speak with the specialist"
- "I want with the specialist"
- "I want to talk with the agent"
- "I want to talk with an agent"
- "I want to talk with the agent"
- "I want to talk with an agent"
- "Let me speak with a specialist"
- "Let me speak with the specialist" 
- "Need to speak with a specialist"
- "Need to speak with the specialist"
- "Please let me speak with the specialist"
- "Supervisor"
- "Manager"
- "Human agent"
- "Transfer me"
- "Connect me"
- "Escalate"
- "Speak with someone else"
- "Talk to someone else"
- "Another agent"
- "Different agent"

Always call transfer_to_specialist when users request any form of transfer or escalation.

For other questions, be helpful and try to assist directly first."""

        super().__init__(instructions=instructions)
        self.ctx = ctx
        self.transfer_manager = WarmTransferManager(ctx)
        self.conversation_history = ""
        self._session = None
        self.is_specialist_mode = False
        logger.info(f"🎯 SupportAgent initialized with empty conversation history")
    
    def set_session(self, session: AgentSession):
        """Set the session reference"""
        self._session = session
    
    @function_tool()
    async def transfer_to_specialist(
        self,
        context: RunContext,
        reason: str = "Customer requested transfer to specialist"
    ) -> str:
        """
        Transfer the customer to a specialist or human agent when they request it.
        
        Args:
            reason: The reason for the transfer (e.g., "customer wants technical support")
        
        Returns:
            Confirmation message about the transfer
        """
        logger.info(f"🎯 FUNCTION TOOL CALLED: transfer_to_specialist - {reason}")
        
        try:
            # Log conversation history before transfer
            logger.info(f"📚 Conversation history at transfer time: {len(self.conversation_history)} characters")
            logger.info(f"📝 History content: {self.conversation_history}")
            
            # Initiate the actual warm transfer
            success = await self.transfer_manager.initiate_warm_transfer(
                self._session, 
                self.conversation_history
            )
            
            if success:
                logger.info("✅ Function tool transfer completed successfully")
                return "Perfect! I've successfully connected you with a specialist who can help you better. They have been briefed on your situation."
            else:
                logger.error("❌ Function tool transfer failed")
                return "I apologize, but I'm having trouble connecting you to a specialist right now. Let me continue helping you directly."
                
        except Exception as e:
            logger.error(f"❌ Error in transfer_to_specialist function tool: {e}")
            return "I'm sorry, there was a technical issue with the transfer. Let me help you directly instead."
    
    async def on_user_speech_received(self, user_speech: str) -> None:
        """Handle user speech as soon as it's received"""
        try:
            logger.info(f"👤 USER SPEECH RECEIVED: '{user_speech}'")
            
            # Add to conversation history immediately
            self.conversation_history += f"Customer: {user_speech}\n"
            logger.info(f"📝 Updated conversation history (received): {len(self.conversation_history)} chars")
            
            await super().on_user_speech_received(user_speech)
            
        except Exception as e:
            logger.error(f"❌ Error in on_user_speech_received: {e}")
            await super().on_user_speech_received(user_speech)

    async def on_user_speech_committed(self, user_speech: str) -> None:
        """Handle user speech and check for transfer requests"""
        try:
            logger.info(f"👤 USER SPEECH COMMITTED: '{user_speech}'")
            
            # Add to conversation history (backup in case received wasn't called)
            if f"Customer: {user_speech}\n" not in self.conversation_history:
                self.conversation_history += f"Customer: {user_speech}\n"
                logger.info(f"📝 Updated conversation history (committed): {len(self.conversation_history)} chars")
            
            # Continue with normal conversation first
            await super().on_user_speech_committed(user_speech)
            
        except Exception as e:
            logger.error(f"❌ Error in on_user_speech_committed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await super().on_user_speech_committed(user_speech)
    
    async def on_llm_function_call_finished(self, function_call_info) -> None:
        """Handle function calls for transfers"""
        try:
            logger.info(f"🔧 LLM function call finished: {function_call_info}")
            
            # Check if this was a transfer function call
            if hasattr(function_call_info, 'function_name') and function_call_info.function_name == 'transfer_to_specialist':
                logger.info("🎯 TRANSFER FUNCTION CALLED - Initiating warm transfer")
                
                # Initiate the actual transfer
                success = await self.transfer_manager.initiate_warm_transfer(
                    self._session, 
                    self.conversation_history
                )
                
                if success:
                    logger.info("✅ Function call transfer completed successfully")
                else:
                    logger.error("❌ Function call transfer failed")
            
            await super().on_llm_function_call_finished(function_call_info)
        except Exception as e:
            logger.error(f"❌ Error in on_llm_function_call_finished: {e}")
            await super().on_llm_function_call_finished(function_call_info)
    
    async def on_agent_speech_committed(self, agent_speech: str) -> None:
        """Track agent responses in conversation history"""
        try:
            logger.info(f"🤖 Agent said: '{agent_speech}'")
            
            # Add to conversation history
            self.conversation_history += f"Assistant: {agent_speech}\n"
            logger.info(f"📝 Updated conversation history: {len(self.conversation_history)} chars")
            
            await super().on_agent_speech_committed(agent_speech)
            
        except Exception as e:
            logger.error(f"❌ Error in on_agent_speech_committed: {e}")
            await super().on_agent_speech_committed(agent_speech)
    
    def _is_transfer_request(self, user_speech: str) -> bool:
        """Check if user speech contains a transfer request"""
        speech_lower = user_speech.lower()
        
        # Simple and direct transfer indicators
        transfer_indicators = [
            "speak with a specialist",
            "speak with the specialist",
            "want with the specialist",
            "want with a specialist", 
            "want to talk with the agent",
            "want to talk with an agent",
            "talk with the agent",
            "talk with an agent",
            "speak with the agent",
            "speak with an agent",
            "let me speak with a specialist",
            "let me speak with the specialist", 
            "need to speak with a specialist",
            "need to speak with the specialist",
            "please let me speak with the specialist",
            "supervisor",
            "manager",
            "human agent",
            "transfer me",
            "connect me",
            "escalate",
            "speak with someone else",
            "talk to someone else",
            "another agent",
            "different agent"
        ]
        
        # Check for direct matches first
        for indicator in transfer_indicators:
            if indicator in speech_lower:
                logger.info(f"🎯 TRANSFER DETECTED: Found '{indicator}' in '{user_speech}'")
                return True
        
        # Check for keyword combinations
        has_need = "need" in speech_lower or "want" in speech_lower or "can i" in speech_lower
        has_speak = "speak" in speech_lower or "talk" in speech_lower
        has_specialist = ("specialist" in speech_lower or "supervisor" in speech_lower or 
                         "agent" in speech_lower or "space" in speech_lower or  # Handle speech recognition errors
                         "spice" in speech_lower or "specs" in speech_lower)  # Common misrecognitions
        
        if has_need and has_speak and has_specialist:
            logger.info(f"🎯 TRANSFER DETECTED: Keyword combination in '{user_speech}'")
            return True
        
        # Single word indicators that are strong signals
        strong_indicators = ["supervisor", "escalate", "manager"]
        for indicator in strong_indicators:
            if indicator in speech_lower:
                logger.info(f"🎯 TRANSFER DETECTED: Strong indicator '{indicator}' in '{user_speech}'")
                return True
        
        logger.info(f"ℹ️ No transfer detected in: '{user_speech}'")
        return False


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint using LiveKit's official warm transfer pattern"""
    logger.info("🚀 Starting LiveKit SupportAgent with warm transfer capability")
    
    # Create the main support agent
    support_agent = SupportAgent(ctx)
    
    # Create agent session with simplified Cartesia TTS
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=groq.LLM(model="llama-3.1-8b-instant"),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        preemptive_generation=False,  # Disable preemptive generation to reduce TTS load
    )

    # Set session reference in agent
    support_agent.set_session(session)

    # Start the session
    await session.start(
        room=ctx.room,
        agent=support_agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )
    
    # Initial greeting
    greeting = "Hello! I'm your AI assistant. How can I help you today? If you need to speak with a specialist, just let me know!"
    await session.say(greeting, allow_interruptions=False)
    
    # Add initial greeting to conversation history
    support_agent.conversation_history += f"Assistant: {greeting}\n"
    logger.info(f"📝 Added greeting to conversation history: {len(support_agent.conversation_history)} chars")

    # Start conversation
    await session.generate_reply(
        instructions="Greet the user and offer assistance. Listen for transfer requests and handle them appropriately."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))