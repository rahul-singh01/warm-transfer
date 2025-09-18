from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import logging

from models.room import (
    CreateRoomRequest, CreateRoomResponse,
    JoinTokenRequest, JoinTokenResponse,
    TransferRequest, TransferResponse,
    CompleteConsultationRequest, CompleteConsultationResponse,
    RoomInfo, TransferInfo,
    ErrorResponse, RoomType, TransferStatus
)
from services.livekit_service import livekit_service
from services.transfer_service import transfer_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rooms", tags=["rooms"])

@router.post("/create", response_model=CreateRoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new LiveKit room"""
    try:
        room_id = await livekit_service.create_room(
            room_name=request.room_name,
            room_type=request.room_type,
            max_participants=request.max_participants
        )
        
        return CreateRoomResponse(
            room_id=room_id,
            room_name=request.room_name,
            room_type=request.room_type,
            created_at=datetime.now(),
            livekit_url=livekit_service.livekit_url
        )
        
    except Exception as e:
        logger.error(f"Failed to create room: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer", response_model=TransferResponse)
async def initiate_transfer(request: TransferRequest):
    """Initiate a warm transfer between agents"""
    try:
        # Validate that the original room exists
        room_info = await livekit_service.get_room_info(request.room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {request.room_id} not found")

        # Infer caller and agent identities if not provided
        caller_identity = request.caller_identity
        agent_a_identity = request.agent_a_identity
        
        if not caller_identity or not agent_a_identity:
            # Get participants from room to infer identities
            participants = room_info.participants
            
            if not caller_identity:
                # Find the caller (participant with role 'caller')
                for identity, participant in participants.items():
                    if participant.role.value == 'caller':
                        caller_identity = identity
                        break
                
                if not caller_identity:
                    # If no specific caller role, use the first participant
                    caller_identity = list(participants.keys())[0] if participants else "caller"
            
            if not agent_a_identity:
                # Find the current agent (participant with role 'agent_a' or first non-caller)
                for identity, participant in participants.items():
                    if participant.role.value == 'agent_a' or (participant.role.value != 'caller' and identity != caller_identity):
                        agent_a_identity = identity
                        break
                
                if not agent_a_identity:
                    agent_a_identity = "agent_a"

        transfer_id, consult_room_id, token_agent_a, token_agent_b = await transfer_service.initiate_warm_transfer(
            original_room_id=request.room_id,
            caller_identity=caller_identity,
            agent_a_identity=agent_a_identity,
            agent_b_identity=request.target_agent_id,
            context=request.call_summary
        )

        return TransferResponse(
            transfer_id=transfer_id,
            consult_room_id=consult_room_id,
            consult_token_agent_a=token_agent_a,
            consult_token_agent_b=token_agent_b,
            status=TransferStatus.IN_PROGRESS,
            created_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"Failed to initiate transfer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer/{transfer_id}/complete-consultation", response_model=CompleteConsultationResponse)
async def complete_consultation(transfer_id: str, request: CompleteConsultationRequest):
    """Signal that Agent A has completed consultation with Agent B"""
    try:
        await transfer_service.signal_consultation_complete(transfer_id, request.agent_identity)
        
        return CompleteConsultationResponse(
            success=True,
            message=f"Consultation completed for transfer {transfer_id}",
            transfer_id=transfer_id,
            completed_at=datetime.now()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to complete consultation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{room_id}/complete-transfer")
async def complete_transfer(room_id: str, transfer_id: str, target_room_id: Optional[str] = None):
    """Complete a warm transfer (legacy endpoint)"""
    try:
        # This endpoint is kept for backward compatibility
        # The new flow uses the consultation completion endpoint above
        success = await livekit_service.complete_transfer(transfer_id, target_room_id)
        
        if success:
            return {"success": True, "message": "Transfer completed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to complete transfer")
            
    except Exception as e:
        logger.error(f"Failed to complete transfer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{room_id}")
async def delete_room(room_id: str):
    """Delete a room"""
    try:
        success = await livekit_service.delete_room(room_id)
        
        if success:
            return {"success": True, "message": f"Room {room_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete room")
            
    except Exception as e:
        logger.error(f"Failed to delete room: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}", response_model=RoomInfo)
async def get_room_info(room_id: str):
    """Get room information"""
    try:
        room_state = await livekit_service.get_room_info(room_id)
        
        if not room_state:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        return RoomInfo(
            room_id=room_state.room_id,
            room_name=room_state.metadata.get("name", room_id),
            room_type=room_state.room_type,
            created_at=room_state.created_at,
            participants=list(room_state.participants.values()),
            is_active=room_state.is_active,
            metadata=room_state.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get room info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[RoomInfo])
async def list_rooms():
    """List all active rooms"""
    try:
        room_states = await livekit_service.list_rooms()
        
        return [
            RoomInfo(
                room_id=room.room_id,
                room_name=room.metadata.get("name", room.room_id),
                room_type=room.room_type,
                created_at=room.created_at,
                participants=list(room.participants.values()),
                is_active=room.is_active,
                metadata=room.metadata
            )
            for room in room_states
        ]
        
    except Exception as e:
        logger.error(f"Failed to list rooms: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transfers/{transfer_id}", response_model=TransferInfo)
async def get_transfer_info(transfer_id: str):
    """Get transfer information"""
    try:
        transfer_state = transfer_service.get_transfer_status(transfer_id)

        if not transfer_state:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")

        return TransferInfo(
            transfer_id=transfer_state.transfer_id,
            original_room_id=transfer_state.original_room,
            consult_room_id=transfer_state.consult_room,
            target_room_id=transfer_state.target_room,
            caller_identity=transfer_state.participants["caller"],
            agent_a_identity=transfer_state.participants["agent_a"],
            agent_b_identity=transfer_state.participants["agent_b"],
            status=transfer_state.status,
            created_at=transfer_state.created_at,
            completed_at=transfer_state.updated_at if transfer_state.status == TransferStatus.COMPLETED else None,
            error_message=transfer_state.error_details
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transfer info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transfers/{transfer_id}/steps")
async def get_transfer_steps(transfer_id: str):
    """Get transfer workflow steps"""
    try:
        steps = transfer_service.get_transfer_steps(transfer_id)

        if not steps:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")

        return {
            "transfer_id": transfer_id,
            "steps": [step.value for step in steps],
            "current_step": steps[-1].value if steps else None,
            "total_steps": len(steps)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transfer steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transfers/", response_model=List[TransferInfo])
async def list_transfers():
    """List all transfers"""
    try:
        transfer_states = await livekit_service.list_transfers()
        
        return [
            TransferInfo(
                transfer_id=transfer.transfer_id,
                original_room_id=transfer.original_room,
                consult_room_id=transfer.consult_room,
                target_room_id=transfer.target_room,
                caller_identity=transfer.participants["caller"],
                agent_a_identity=transfer.participants["agent_a"],
                agent_b_identity=transfer.participants["agent_b"],
                status=transfer.status,
                created_at=transfer.created_at,
                completed_at=transfer.updated_at if transfer.status == TransferStatus.COMPLETED else None,
                error_message=transfer.error_details
            )
            for transfer in transfer_states
        ]
        
    except Exception as e:
        logger.error(f"Failed to list transfers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_inactive_rooms(max_age_minutes: int = 60):
    """Clean up inactive rooms"""
    try:
        cleaned_count = await livekit_service.cleanup_inactive_rooms(max_age_minutes)
        return {"success": True, "cleaned_rooms": cleaned_count}
        
    except Exception as e:
        logger.error(f"Failed to cleanup rooms: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Transfer workflow is now handled by the transfer_service
