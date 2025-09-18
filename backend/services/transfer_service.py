import asyncio
import uuid
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from .livekit_service import livekit_service
from .ai_service import ai_service, tts_service
from models.room import (
    TransferStatus, TransferState, ParticipantRole,
    TranscriptEntry, CallSummaryResponse, RoomType
)

logger = logging.getLogger(__name__)

class TransferStep(str, Enum):
    INITIATED = "initiated"
    CALLER_ON_HOLD = "caller_on_hold"
    CONSULT_ROOM_CREATED = "consult_room_created"
    AGENTS_CONNECTED = "agents_connected"
    SUMMARY_GENERATED = "summary_generated"
    SUMMARY_PLAYED = "summary_played"
    CONSULTATION_COMPLETE = "consultation_complete"
    TRANSFER_COMPLETE = "transfer_complete"
    FAILED = "failed"

class WarmTransferService:
    def __init__(self):
        self.active_transfers: Dict[str, TransferState] = {}
        self.transfer_steps: Dict[str, List[TransferStep]] = {}
        
    async def initiate_warm_transfer(
        self,
        original_room_id: str,
        caller_identity: str,
        agent_a_identity: str,
        agent_b_identity: str,
        context: Optional[str] = None,
        conversation_history: Optional[str] = None
    ) -> Tuple[str, str, str, str]:
        """
        Initiate the complete warm transfer process
        Returns: (transfer_id, consult_room_id, token_agent_a, token_agent_b)
        """
        try:
            transfer_id = f"transfer_{uuid.uuid4().hex[:8]}"
            logger.info(f"Initiating warm transfer {transfer_id}")
            
            # Step 1: Create consultation room
            consult_room_id = await livekit_service.create_room(
                f"Consultation_{transfer_id}",
                room_type=RoomType.CONSULTATION,
                max_participants=3
            )
            
            # Step 2: Generate tokens for agents
            token_agent_a = await livekit_service.generate_join_token(
                consult_room_id,
                agent_a_identity,
                f"Agent A ({agent_a_identity})",
                ParticipantRole.AGENT_A
            )
            
            token_agent_b = await livekit_service.generate_join_token(
                consult_room_id,
                agent_b_identity,
                f"Agent B ({agent_b_identity})",
                ParticipantRole.AGENT_B
            )
            
            # Initialize transfer state
            transfer_state = TransferState(
                transfer_id=transfer_id,
                status=TransferStatus.IN_PROGRESS,
                original_room=original_room_id,
                consult_room=consult_room_id,
                participants={
                    "caller": caller_identity,
                    "agent_a": agent_a_identity,
                    "agent_b": agent_b_identity
                },
                created_at=datetime.now(),
                updated_at=datetime.now(),
                steps_completed=[TransferStep.INITIATED.value, TransferStep.CONSULT_ROOM_CREATED.value],
                call_summary=context,
                conversation_history=conversation_history
            )
            
            self.active_transfers[transfer_id] = transfer_state
            self.transfer_steps[transfer_id] = [TransferStep.INITIATED, TransferStep.CONSULT_ROOM_CREATED]
            
            # Step 3: Start the transfer workflow in background
            asyncio.create_task(self._execute_transfer_workflow(transfer_id))
            
            logger.info(f"Transfer {transfer_id} initiated successfully")
            return transfer_id, consult_room_id, token_agent_a, token_agent_b
            
        except Exception as e:
            logger.error(f"Failed to initiate transfer: {e}")
            raise
    
    async def _execute_transfer_workflow(self, transfer_id: str):
        """Execute the complete warm transfer workflow"""
        try:
            transfer_state = self.active_transfers[transfer_id]
            
            # Step 1: Put caller on hold
            await self._put_caller_on_hold(transfer_id)
            
            # Step 2: Wait for agents to join consultation room
            await self._wait_for_agents_connection(transfer_id)
            
            # Step 3: Generate and play call summary
            await self._generate_and_play_summary(transfer_id)
            
            await self._wait_for_consultation_completion(transfer_id)
            
            
        except Exception as e:
            logger.error(f"Transfer workflow failed for {transfer_id}: {e}")
            await self._mark_transfer_failed(transfer_id, str(e))
    
    async def _put_caller_on_hold(self, transfer_id: str):
        """Put the caller on hold with music"""
        try:
            transfer_state = self.active_transfers[transfer_id]
            caller_identity = transfer_state.participants["caller"]
            original_room = transfer_state.original_room
            
            # TODO: Implement actual hold functionality
            # This would involve:
            # 1. Muting caller's microphone
            # 2. Playing hold music
            # 3. Showing hold UI
            
            logger.info(f"Put caller {caller_identity} on hold in room {original_room}")
            
            self.transfer_steps[transfer_id].append(TransferStep.CALLER_ON_HOLD)
            transfer_state.steps_completed.append(TransferStep.CALLER_ON_HOLD.value)
            transfer_state.updated_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to put caller on hold for transfer {transfer_id}: {e}")
            raise
    
    async def _wait_for_agents_connection(self, transfer_id: str, timeout: int = 60):
        """Wait for both agents to connect to consultation room"""
        try:
            transfer_state = self.active_transfers[transfer_id]
            consult_room_id = transfer_state.consult_room
            
            start_time = datetime.now()
            
            while (datetime.now() - start_time).seconds < timeout:
                room_info = await livekit_service.get_room_info(consult_room_id)
                
                if room_info and len(room_info.participants) >= 2:
                    # Check if we have both Agent A and Agent B
                    agent_roles = [p.role for p in room_info.participants.values()]
                    
                    if (ParticipantRole.AGENT_A in agent_roles and 
                        ParticipantRole.AGENT_B in agent_roles):
                        
                        logger.info(f"Both agents connected for transfer {transfer_id}")
                        self.transfer_steps[transfer_id].append(TransferStep.AGENTS_CONNECTED)
                        transfer_state.steps_completed.append(TransferStep.AGENTS_CONNECTED.value)
                        transfer_state.updated_at = datetime.now()
                        return
                
                await asyncio.sleep(2)
            
            raise TimeoutError(f"Agents did not connect within {timeout} seconds")
            
        except Exception as e:
            logger.error(f"Failed waiting for agents connection for transfer {transfer_id}: {e}")
            raise
    
    async def _generate_and_play_summary(self, transfer_id: str):
        """Generate AI summary and play it in consultation room"""
        try:
            transfer_state = self.active_transfers[transfer_id]
            original_room = transfer_state.original_room
            consult_room_id = transfer_state.consult_room
            
            # Get transcript from original room
            transcript_entries = await self._get_room_transcript(original_room)
            
            if not transcript_entries:
                # Create mock transcript for demo
                transcript_entries = self._create_mock_transcript(original_room)
            
            # Generate call summary
            summary_response = await ai_service.generate_call_summary(
                transcript_entries=transcript_entries,
                room_id=original_room,
                context="Warm transfer consultation"
            )
            
            logger.info(f"Generated call summary for transfer {transfer_id}")
            self.transfer_steps[transfer_id].append(TransferStep.SUMMARY_GENERATED)
            transfer_state.steps_completed.append(TransferStep.SUMMARY_GENERATED.value)
            
            # Generate briefing for Agent B
            agent_b_identity = transfer_state.participants["agent_b"]
            briefing = await ai_service.generate_transfer_briefing(
                call_summary=summary_response.content,
                agent_b_name=f"Agent B ({agent_b_identity})",
                caller_name="Customer"
            )
            
            # Convert briefing to speech (if TTS is available)
            audio_data = await tts_service.text_to_speech(briefing)
            
            # Send summary data to consultation room
            await self._send_summary_to_room(consult_room_id, summary_response, briefing)
            
            logger.info(f"Played call summary for transfer {transfer_id}")
            self.transfer_steps[transfer_id].append(TransferStep.SUMMARY_PLAYED)
            transfer_state.steps_completed.append(TransferStep.SUMMARY_PLAYED.value)
            transfer_state.updated_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to generate/play summary for transfer {transfer_id}: {e}")
            raise
    
    async def _send_summary_to_room(
        self, 
        room_id: str, 
        summary: CallSummaryResponse, 
        briefing: str
    ):
        """Send summary data to consultation room participants"""
        try:
            # TODO: Implement sending data to LiveKit room
            # This would use LiveKit's data channel to send the summary
            logger.info(f"Sent summary to consultation room {room_id}")
            
        except Exception as e:
            logger.error(f"Failed to send summary to room {room_id}: {e}")
            raise
    
    async def _wait_for_consultation_completion(self, transfer_id: str, timeout: int = 300):
        """Wait for agents to complete their consultation"""
        try:
        
            consultation_time = 10  # 10 seconds for demo
            await asyncio.sleep(consultation_time)
            
            transfer_state = self.active_transfers[transfer_id]
            self.transfer_steps[transfer_id].append(TransferStep.CONSULTATION_COMPLETE)
            transfer_state.steps_completed.append(TransferStep.CONSULTATION_COMPLETE.value)
            transfer_state.updated_at = datetime.now()
            
            logger.info(f"Consultation completed for transfer {transfer_id} (simulated after {consultation_time}s)")
            
        except Exception as e:
            logger.error(f"Failed waiting for consultation completion for transfer {transfer_id}: {e}")
            raise
    
    async def signal_consultation_complete(self, transfer_id: str, agent_identity: str):
        """Signal that consultation is complete and transfer should proceed"""
        try:
            transfer_state = self.active_transfers.get(transfer_id)
            if not transfer_state:
                raise ValueError(f"Transfer {transfer_id} not found")
            
            # Verify the agent calling this is Agent A
            if agent_identity != transfer_state.participants["agent_a"]:
                raise ValueError(f"Only Agent A can signal consultation completion")
            
            # Mark consultation as complete
            if TransferStep.CONSULTATION_COMPLETE not in self.transfer_steps[transfer_id]:
                self.transfer_steps[transfer_id].append(TransferStep.CONSULTATION_COMPLETE)
                transfer_state.steps_completed.append(TransferStep.CONSULTATION_COMPLETE.value)
                transfer_state.updated_at = datetime.now()
                
                logger.info(f"Agent A ({agent_identity}) signaled consultation complete for {transfer_id}")
                
                # Trigger immediate transfer completion
                await self._complete_transfer(transfer_id)
            
        except Exception as e:
            logger.error(f"Failed to signal consultation completion: {e}")
            raise
    
    async def _complete_transfer(self, transfer_id: str):
        """Complete the warm transfer - Agent A exits, Agent B joins caller"""
        try:
            transfer_state = self.active_transfers[transfer_id]
            original_room = transfer_state.original_room
            consult_room_id = transfer_state.consult_room
            
            caller_identity = transfer_state.participants["caller"]
            agent_a_identity = transfer_state.participants["agent_a"]
            agent_b_identity = transfer_state.participants["agent_b"]
            
            logger.info(f"Starting transfer completion: Agent A ({agent_a_identity}) -> Agent B ({agent_b_identity})")
            
            # Step 1: Generate token for Agent B to join original room with caller
            agent_b_token = await livekit_service.generate_join_token(
                original_room,
                agent_b_identity,
                f"Agent B ({agent_b_identity})",
                ParticipantRole.AGENT_B
            )
            
            logger.info(f"Generated token for Agent B to join original room {original_room}")
            
           
            await asyncio.sleep(2)
            
            try:
                await livekit_service.remove_participant(original_room, agent_a_identity)
                logger.info(f"Removed Agent A ({agent_a_identity}) from original room {original_room}")
            except Exception as e:
                logger.warning(f"Could not remove Agent A from original room: {e}")
            
            try:
                await livekit_service.delete_room(consult_room_id)
                logger.info(f"Deleted consultation room {consult_room_id}")
            except Exception as e:
                logger.warning(f"Could not delete consultation room: {e}")
            
            # Step 6: Update transfer state to completed
            transfer_state.status = TransferStatus.COMPLETED
            transfer_state.target_room = original_room
            transfer_state.agent_b_token = agent_b_token
            transfer_state.updated_at = datetime.now()
            self.transfer_steps[transfer_id].append(TransferStep.TRANSFER_COMPLETE)
            transfer_state.steps_completed.append(TransferStep.TRANSFER_COMPLETE.value)
            
            logger.info(f"Transfer {transfer_id} completed successfully")
            logger.info(f"Final state: Caller ({caller_identity}) + Agent B ({agent_b_identity}) in room {original_room}")
            
        except Exception as e:
            logger.error(f"Failed to complete transfer {transfer_id}: {e}")
            await self._mark_transfer_failed(transfer_id, str(e))
            raise
    
    async def _mark_transfer_failed(self, transfer_id: str, error_message: str):
        """Mark transfer as failed"""
        try:
            transfer_state = self.active_transfers[transfer_id]
            transfer_state.status = TransferStatus.FAILED
            transfer_state.error_details = error_message
            transfer_state.updated_at = datetime.now()
            self.transfer_steps[transfer_id].append(TransferStep.FAILED)
            
            logger.error(f"Transfer {transfer_id} marked as failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to mark transfer as failed: {e}")
    
    async def _get_room_transcript(self, room_id: str) -> List[TranscriptEntry]:
        """Get transcript entries for a room"""
        # In production, this would fetch from database
        return []
    
    def _create_mock_transcript(self, room_id: str) -> List[TranscriptEntry]:
        """Create mock transcript for demonstration"""
        base_time = datetime.now()
        
        return [
            TranscriptEntry(
                speaker_identity="caller_001",
                speaker_name="Customer",
                text="Hi, I'm having trouble with my recent order. It hasn't arrived yet.",
                timestamp=base_time,
                confidence=0.95
            ),
            TranscriptEntry(
                speaker_identity="agent_a_001",
                speaker_name="Agent Sarah",
                text="I'm sorry to hear about that. Let me check your order status and see how I can help you.",
                timestamp=base_time,
                confidence=0.98
            )
        ]
    
    def get_transfer_status(self, transfer_id: str) -> Optional[TransferState]:
        """Get current transfer status"""
        return self.active_transfers.get(transfer_id)
    
    def get_transfer_steps(self, transfer_id: str) -> List[TransferStep]:
        """Get completed transfer steps"""
        return self.transfer_steps.get(transfer_id, [])

# Global service instance
transfer_service = WarmTransferService()
