from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timedelta
import logging

from models.room import (
    JoinTokenRequest, JoinTokenResponse,
    ParticipantInfo, HoldRequest, HoldResponse,
    ErrorResponse
)
from services.livekit_service import livekit_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/participants", tags=["participants"])

@router.post("/token", response_model=JoinTokenResponse)
async def generate_join_token(request: JoinTokenRequest):
    """Generate a join token for a participant"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(request.room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {request.room_id} not found")
        
        # Generate the token
        token = await livekit_service.generate_join_token(
            room_id=request.room_id,
            identity=request.identity,
            name=request.name,
            role=request.role,
            metadata=request.metadata
        )
        
        return JoinTokenResponse(
            token=token,
            url=livekit_service.livekit_url,
            room_id=request.room_id,
            identity=request.identity,
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate join token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{identity}")
async def remove_participant(identity: str, room_id: str):
    """Remove a participant from a room"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        # Check if participant exists in the room
        if identity not in room_info.participants:
            raise HTTPException(status_code=404, detail=f"Participant {identity} not found in room {room_id}")
        
        # Remove the participant
        success = await livekit_service.remove_participant(room_id, identity)
        
        if success:
            return {"success": True, "message": f"Participant {identity} removed from room {room_id}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove participant")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove participant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/move")
async def move_participant(
    identity: str,
    from_room_id: str,
    to_room_id: str,
    new_role: str = None
):
    """Move a participant from one room to another"""
    try:
        # Validate source room
        from_room = await livekit_service.get_room_info(from_room_id)
        if not from_room:
            raise HTTPException(status_code=404, detail=f"Source room {from_room_id} not found")
        
        # Validate target room
        to_room = await livekit_service.get_room_info(to_room_id)
        if not to_room:
            raise HTTPException(status_code=404, detail=f"Target room {to_room_id} not found")
        
        # Check if participant exists in source room
        if identity not in from_room.participants:
            raise HTTPException(status_code=404, detail=f"Participant {identity} not found in room {from_room_id}")
        
        participant = from_room.participants[identity]
        
        # Generate new token for target room
        new_token = await livekit_service.generate_join_token(
            room_id=to_room_id,
            identity=identity,
            name=participant.name,
            role=participant.role if not new_role else new_role,
            metadata=participant.metadata
        )
        
        # Remove from source room
        await livekit_service.remove_participant(from_room_id, identity)
        
        return {
            "success": True,
            "message": f"Participant {identity} moved from {from_room_id} to {to_room_id}",
            "new_token": new_token,
            "new_room_url": livekit_service.livekit_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to move participant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}", response_model=List[ParticipantInfo])
async def list_participants(room_id: str):
    """List all participants in a room"""
    try:
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        return list(room_info.participants.values())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list participants: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}/{identity}", response_model=ParticipantInfo)
async def get_participant_info(room_id: str, identity: str):
    """Get information about a specific participant"""
    try:
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        if identity not in room_info.participants:
            raise HTTPException(status_code=404, detail=f"Participant {identity} not found in room {room_id}")
        
        return room_info.participants[identity]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get participant info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hold", response_model=HoldResponse)
async def put_participant_on_hold(request: HoldRequest):
    """Put a participant on hold (placeholder for future implementation)"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(request.room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {request.room_id} not found")
        
        # Check if participant exists in the room
        if request.participant_identity not in room_info.participants:
            raise HTTPException(
                status_code=404, 
                detail=f"Participant {request.participant_identity} not found in room {request.room_id}"
            )
        
        # TODO: Implement actual hold functionality
        # This would involve:
        # 1. Muting the participant's audio/video
        # 2. Playing hold music
        # 3. Updating participant metadata
        
        logger.info(f"Put participant {request.participant_identity} on hold in room {request.room_id}")
        
        return HoldResponse(
            success=True,
            participant_identity=request.participant_identity,
            is_on_hold=True,
            hold_started_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to put participant on hold: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unhold")
async def remove_participant_from_hold(room_id: str, participant_identity: str):
    """Remove a participant from hold (placeholder for future implementation)"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        # Check if participant exists in the room
        if participant_identity not in room_info.participants:
            raise HTTPException(
                status_code=404, 
                detail=f"Participant {participant_identity} not found in room {room_id}"
            )
        
        # TODO: Implement actual unhold functionality
        # This would involve:
        # 1. Unmuting the participant's audio/video
        # 2. Stopping hold music
        # 3. Updating participant metadata
        
        logger.info(f"Removed participant {participant_identity} from hold in room {room_id}")
        
        return HoldResponse(
            success=True,
            participant_identity=participant_identity,
            is_on_hold=False,
            hold_started_at=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove participant from hold: {e}")
        raise HTTPException(status_code=500, detail=str(e))
