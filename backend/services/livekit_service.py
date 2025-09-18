import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import aiohttp

# Import actual LiveKit SDK
from livekit.api import (
    AccessToken, VideoGrants, 
    CreateRoomRequest, DeleteRoomRequest, ListRoomsRequest,
    room_service
)

from models.room import (
    RoomType, ParticipantRole, TransferStatus,
    RoomState, TransferState, ParticipantInfo
)

logger = logging.getLogger(__name__)

class LiveKitService:
    def __init__(self, validate_config: bool = True):
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")
        self.livekit_url = os.getenv("LIVEKIT_URL")
        
        if validate_config and not all([self.api_key, self.api_secret, self.livekit_url]):
            raise ValueError("Missing LiveKit configuration. Please set LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL")
        
        # Initialize session and room service lazily
        self.session = None
        self.room_service = None
        self._initialized = False
        
        # In-memory state management (in production, use Redis or database)
        self.rooms: Dict[str, RoomState] = {}
        self.transfers: Dict[str, TransferState] = {}
    
    async def _ensure_initialized(self):
        """Ensure the service is initialized with session and room service"""
        if not self._initialized:
            self.session = aiohttp.ClientSession()
            if self.livekit_url and self.api_key and self.api_secret:
                self.room_service = room_service.RoomService(
                    session=self.session,
                    url=self.livekit_url,
                    api_key=self.api_key,
                    api_secret=self.api_secret
                )
            self._initialized = True
    
    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        
    async def create_room(self, room_name: str, room_type: RoomType = RoomType.CALL, max_participants: int = 10) -> str:
        """Create a new LiveKit room"""
        try:
            room_id = f"{room_type.value}_{uuid.uuid4().hex[:8]}"
            
            # For now, just create room locally - LiveKit will create it when first participant joins
            logger.info(f"Creating room {room_id} (will be created in LiveKit when first participant joins)")
            
            # Store room state
            self.rooms[room_id] = RoomState(
                room_id=room_id,
                room_type=room_type,
                participants={},
                created_at=datetime.now(),
                last_activity=datetime.now(),
                is_active=True,
                metadata={"name": room_name, "max_participants": max_participants}
            )
            
            logger.info(f"Created room {room_id} of type {room_type.value}")
            return room_id
            
        except Exception as e:
            logger.error(f"Failed to create room: {e}")
            raise
    
    async def generate_join_token(
        self, 
        room_id: str, 
        identity: str, 
        name: str, 
        role: ParticipantRole = ParticipantRole.CALLER,
        metadata: Optional[Dict] = None
    ) -> str:
        """Generate a join token for a participant"""
        try:
            await self._ensure_initialized()
            
            # Check if room exists locally, if not try to get from LiveKit or create entry
            if room_id not in self.rooms:
                logger.info(f"Room {room_id} not in local state, checking LiveKit or creating entry...")
                room_info = await self.get_room_info(room_id)
                if not room_info:
                    # Create a minimal room entry for rooms that exist in LiveKit but not locally
                    logger.info(f"Creating minimal room entry for {room_id}")
                    self.rooms[room_id] = RoomState(
                        room_id=room_id,
                        room_type=RoomType.CALL,  # Default type
                        participants={},
                        created_at=datetime.now(),
                        last_activity=datetime.now(),
                        is_active=True,
                        metadata={"auto_created": True}
                    )
            
            # Create actual LiveKit access token
            token = AccessToken(self.api_key, self.api_secret)
            token.with_identity(identity)
            token.with_name(name)
            
            # Grant access to the room
            video_grant = VideoGrants(
                room_join=True,
                room=room_id,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
            token.with_grants(video_grant)
            
            # Set token expiration
            token.with_ttl(timedelta(hours=24))
            
            # Add metadata to token
            participant_metadata = {
                "role": role.value,
                "joined_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            token.with_metadata(str(participant_metadata))
            
            jwt_token = token.to_jwt()
            
            # Update room state
            room_state = self.rooms[room_id]
            room_state.participants[identity] = ParticipantInfo(
                identity=identity,
                name=name,
                role=role,
                is_connected=False,
                joined_at=datetime.now(),
                audio_enabled=True,
                video_enabled=True,
                is_speaking=False,
                metadata=participant_metadata
            )
            room_state.last_activity = datetime.now()
            
            logger.info(f"Generated token for {identity} in room {room_id}")
            return jwt_token
            
        except Exception as e:
            logger.error(f"Failed to generate token: {e}")
            raise
    
    async def initiate_transfer(
        self,
        original_room_id: str,
        caller_identity: str,
        agent_a_identity: str,
        agent_b_identity: str,
        context: Optional[str] = None,
        conversation_history: Optional[str] = None
    ) -> Tuple[str, str, str, str]:
        """
        Initiate warm transfer process
        Returns: (transfer_id, consult_room_id, token_agent_a, token_agent_b)
        """
        try:
            transfer_id = f"transfer_{uuid.uuid4().hex[:8]}"
            
            # Create consultation room for Agent A and Agent B
            consult_room_id = await self.create_room(
                f"Consultation_{transfer_id}",
                RoomType.CONSULTATION,
                max_participants=3  # Agent A, Agent B, and AI agent
            )
            
            # Generate tokens for both agents
            token_agent_a = await self.generate_join_token(
                consult_room_id,
                agent_a_identity,
                f"Agent A ({agent_a_identity})",
                ParticipantRole.AGENT_A
            )
            
            token_agent_b = await self.generate_join_token(
                consult_room_id,
                agent_b_identity,
                f"Agent B ({agent_b_identity})",
                ParticipantRole.AGENT_B
            )
            
            # Store transfer state
            self.transfers[transfer_id] = TransferState(
                transfer_id=transfer_id,
                status=TransferStatus.PENDING,
                original_room=original_room_id,
                consult_room=consult_room_id,
                participants={
                    "caller": caller_identity,
                    "agent_a": agent_a_identity,
                    "agent_b": agent_b_identity
                },
                created_at=datetime.now(),
                updated_at=datetime.now(),
                steps_completed=["consult_room_created"],
                call_summary=context,
                conversation_history=conversation_history
            )
            
            logger.info(f"Initiated transfer {transfer_id} from room {original_room_id}")
            return transfer_id, consult_room_id, token_agent_a, token_agent_b
            
        except Exception as e:
            logger.error(f"Failed to initiate transfer: {e}")
            raise
    
    async def complete_transfer(
        self,
        transfer_id: str,
        target_room_id: Optional[str] = None
    ) -> bool:
        """Complete the warm transfer by moving participants"""
        try:
            if transfer_id not in self.transfers:
                raise ValueError(f"Transfer {transfer_id} not found")
            
            transfer_state = self.transfers[transfer_id]
            
            # If no target room specified, use the original room
            if not target_room_id:
                target_room_id = transfer_state.original_room
            
            # Move Agent B to the target room with caller
            agent_b_token = await self.generate_join_token(
                target_room_id,
                transfer_state.participants["agent_b"],
                f"Agent B ({transfer_state.participants['agent_b']})",
                ParticipantRole.AGENT_B
            )
            
            # Store the token for Agent B to join
            transfer_state.agent_b_token = agent_b_token
            
            # Remove Agent A from original room (they should disconnect)
            await self.remove_participant(
                transfer_state.original_room,
                transfer_state.participants["agent_a"]
            )
            
            # Update transfer state
            transfer_state.status = TransferStatus.COMPLETED
            transfer_state.target_room = target_room_id
            transfer_state.updated_at = datetime.now()
            transfer_state.steps_completed.append("transfer_completed")
            
            # Clean up consultation room
            await self.delete_room(transfer_state.consult_room)
            
            logger.info(f"Completed transfer {transfer_id} - Agent B token: {agent_b_token[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete transfer {transfer_id}: {e}")
            transfer_state = self.transfers.get(transfer_id)
            if transfer_state:
                transfer_state.status = TransferStatus.FAILED
                transfer_state.error_details = str(e)
                transfer_state.updated_at = datetime.now()
            raise
    
    async def remove_participant(self, room_id: str, identity: str) -> bool:
        """Remove a participant from a room"""
        try:
            # Mock participant removal
            logger.info(f"Mock: Removing participant {identity} from room {room_id}")
            
            # Update room state
            if room_id in self.rooms and identity in self.rooms[room_id].participants:
                del self.rooms[room_id].participants[identity]
                self.rooms[room_id].last_activity = datetime.now()
            
            logger.info(f"Removed participant {identity} from room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove participant {identity} from room {room_id}: {e}")
            raise
    
    async def delete_room(self, room_id: str) -> bool:
        """Delete a room"""
        try:
            await self._ensure_initialized()
            # Delete actual LiveKit room (only if it exists)
            logger.info(f"Deleting LiveKit room {room_id}")
            
            try:
                if self.room_service:
                    delete_request = DeleteRoomRequest(room=room_id)
                    await self.room_service.delete_room(delete_request)
                    logger.info(f"Deleted LiveKit room {room_id}")
            except Exception as livekit_error:
                # Room might not exist in LiveKit if no participants ever joined
                logger.warning(f"Could not delete room {room_id} from LiveKit (might not exist): {livekit_error}")
            
            # Remove from local state regardless
            if room_id in self.rooms:
                del self.rooms[room_id]
                logger.info(f"Removed room {room_id} from local state")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete room {room_id}: {e}")
            raise
    
    async def get_room_info(self, room_id: str) -> Optional[RoomState]:
        """Get room information"""
        try:
            await self._ensure_initialized()
            # Check local state first
            local_room = self.rooms.get(room_id)
            if not local_room:
                # Try to get from LiveKit
                try:
                    if self.room_service:
                        list_request = ListRoomsRequest()
                        rooms = await self.room_service.list_rooms(list_request)
                        
                        for room in rooms.rooms:
                            if room.name == room_id:
                                # Get participants from LiveKit
                                participants = {}
                                for participant in room.participants:
                                    participants[participant.identity] = ParticipantInfo(
                                        identity=participant.identity,
                                        name=participant.name or participant.identity,
                                        role=ParticipantRole.CALLER,  # Default role
                                        joined_at=datetime.fromtimestamp(participant.joined_at) if participant.joined_at else datetime.now(),
                                        is_connected=True
                                    )
                                
                                # Create local state entry if found
                                self.rooms[room_id] = RoomState(
                                    room_id=room_id,
                                    room_type=RoomType.CALL,  # Default type
                                    participants=participants,
                                    created_at=datetime.fromtimestamp(room.creation_time),
                                    last_activity=datetime.now(),
                                    is_active=True,
                                    metadata={}
                                )
                                return self.rooms[room_id]
                except Exception as e:
                    logger.warning(f"Could not fetch room {room_id} from LiveKit: {e}")
                
                return None
            
            return local_room
            
        except Exception as e:
            logger.error(f"Failed to get room info for {room_id}: {e}")
            return None
    
    async def get_transfer_info(self, transfer_id: str) -> Optional[TransferState]:
        """Get transfer information"""
        return self.transfers.get(transfer_id)
    
    async def list_rooms(self) -> List[RoomState]:
        """List all active rooms"""
        return [room for room in self.rooms.values() if room.is_active]
    
    async def list_transfers(self) -> List[TransferState]:
        """List all transfers"""
        return list(self.transfers.values())
    
    async def cleanup_inactive_rooms(self, max_age_minutes: int = 60) -> int:
        """Clean up inactive rooms older than max_age_minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        cleaned_count = 0
        
        rooms_to_delete = []
        for room_id, room_state in self.rooms.items():
            if room_state.last_activity < cutoff_time and len(room_state.participants) == 0:
                rooms_to_delete.append(room_id)
        
        for room_id in rooms_to_delete:
            try:
                await self.delete_room(room_id)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to cleanup room {room_id}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} inactive rooms")
        return cleaned_count

# Global service instance - created lazily to avoid config validation during imports
_livekit_service_instance = None

def get_livekit_service() -> LiveKitService:
    """Get or create the global LiveKit service instance"""
    global _livekit_service_instance
    if _livekit_service_instance is None:
        _livekit_service_instance = LiveKitService()
    return _livekit_service_instance

# For backward compatibility - create a lazy service instance
class LazyLiveKitService:
    def __init__(self):
        self._service = None
    
    def __getattr__(self, name):
        if self._service is None:
            self._service = LiveKitService(validate_config=False)
        return getattr(self._service, name)

livekit_service = LazyLiveKitService()
