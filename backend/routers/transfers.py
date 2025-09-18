from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from models.room import (
    TransferRequest, TransferResponse, TransferStatus,
    CompleteConsultationRequest, CompleteConsultationResponse,
    CallSummaryRequest, CallSummaryResponse,
    TransferInfo, ErrorResponse
)
from services.livekit_service import livekit_service
from services.call_summary_service import call_summary_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transfers", tags=["transfers"])

@router.post("/initiate", response_model=TransferResponse)
async def initiate_warm_transfer(request: TransferRequest):
    """
    Initiate a warm transfer process
    
    This endpoint:
    1. Creates a consultation room for Agent A and Agent B
    2. Generates tokens for both agents to join the consultation
    3. Returns the transfer ID and consultation room details
    """
    try:
        logger.info(f"Initiating transfer for room {request.room_id} (validation temporarily disabled)")
        
        caller_identity = request.caller_identity or "caller"
        agent_a_identity = request.agent_a_identity or "agent_a"
        
        logger.info(f"Transfer participants - Caller: {caller_identity}, Agent A: {agent_a_identity}, Target: {request.target_agent_id}")
        
        transfer_id, consult_room_id, token_agent_a, token_agent_b = await livekit_service.initiate_transfer(
            original_room_id=request.room_id,
            caller_identity=caller_identity,
            agent_a_identity=agent_a_identity,
            agent_b_identity=request.target_agent_id
        )
        
        logger.info(f"Initiated warm transfer {transfer_id} from {request.room_id} to agent {request.target_agent_id}")
        
        return TransferResponse(
            transfer_id=transfer_id,
            consult_room_id=consult_room_id,
            consult_token_agent_a=token_agent_a,
            consult_token_agent_b=token_agent_b,
            status=TransferStatus.PENDING,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate warm transfer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/complete/{transfer_id}")
async def complete_warm_transfer(
    transfer_id: str,
    background_tasks: BackgroundTasks,
    target_room_id: Optional[str] = None
):
    """
    Complete the warm transfer process
    
    This endpoint:
    1. Moves Agent B to the original room with the caller
    2. Removes Agent A from the original room
    3. Cleans up the consultation room
    4. Updates transfer status to completed
    """
    try:
        # Get transfer information
        transfer_info = await livekit_service.get_transfer_info(transfer_id)
        if not transfer_info:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        if transfer_info.status not in [TransferStatus.PENDING, TransferStatus.IN_PROGRESS]:
            raise HTTPException(
                status_code=400, 
                detail=f"Transfer {transfer_id} cannot be completed from {transfer_info.status} status"
            )
        
        # Complete the transfer
        success = await livekit_service.complete_transfer(transfer_id, target_room_id)
        
        if success:
            # Schedule cleanup in background
            background_tasks.add_task(cleanup_transfer_resources, transfer_id)
            
            # Get updated transfer info to include Agent B token
            updated_transfer_info = await livekit_service.get_transfer_info(transfer_id)
            agent_b_token = getattr(updated_transfer_info, 'agent_b_token', None)
            
            return {
                "success": True,
                "message": f"Transfer {transfer_id} completed successfully",
                "transfer_id": transfer_id,
                "target_room_id": target_room_id or transfer_info.original_room,
                "agent_b_token": agent_b_token,
                "livekit_url": livekit_service.livekit_url
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to complete transfer")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete transfer {transfer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consultation/complete/{transfer_id}")
async def complete_consultation(
    transfer_id: str,
    request: CompleteConsultationRequest
):
    """
    Complete the consultation phase and prepare for transfer
    
    This endpoint is called when Agent A is ready to transfer the call
    after consulting with Agent B in the consultation room.
    """
    try:
        # Get transfer information
        transfer_info = await livekit_service.get_transfer_info(transfer_id)
        if not transfer_info:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        # Update transfer status to in progress
        transfer_info.status = TransferStatus.IN_PROGRESS
        transfer_info.updated_at = datetime.now()
        transfer_info.steps_completed.append("consultation_completed")
        
        # Store consultation notes if provided
        if request.notes:
            transfer_info.call_summary = request.notes
        
        logger.info(f"Consultation completed for transfer {transfer_id} by {request.agent_identity}")
        
        return CompleteConsultationResponse(
            success=True,
            message="Consultation completed successfully. Ready for transfer.",
            transfer_id=transfer_id,
            completed_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete consultation for transfer {transfer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summary/generate")
async def generate_call_summary(request: CallSummaryRequest):
    """
    Generate a call summary for context sharing during warm transfer
    
    This endpoint generates an AI-powered summary of the call that can be
    shared with Agent B during the consultation phase.
    """
    try:
        # Validate room exists
        room_info = await livekit_service.get_room_info(request.room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {request.room_id} not found")
        
        # Generate call summary
        summary = await call_summary_service.generate_summary(
            room_id=request.room_id,
            include_transcript=request.include_transcript,
            max_duration_minutes=request.max_duration_minutes
        )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate call summary for room {request.room_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{transfer_id}", response_model=TransferInfo)
async def get_transfer_status(transfer_id: str):
    """Get the current status of a transfer"""
    try:
        transfer_info = await livekit_service.get_transfer_info(transfer_id)
        if not transfer_info:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        # Convert TransferState to TransferInfo for response
        return TransferInfo(
            transfer_id=transfer_info.transfer_id,
            original_room_id=transfer_info.original_room,
            consult_room_id=transfer_info.consult_room,
            target_room_id=transfer_info.target_room,
            caller_identity=transfer_info.participants.get("caller", ""),
            agent_a_identity=transfer_info.participants.get("agent_a", ""),
            agent_b_identity=transfer_info.participants.get("agent_b", ""),
            status=transfer_info.status,
            call_summary=transfer_info.call_summary,
            created_at=transfer_info.created_at,
            completed_at=None if transfer_info.status != TransferStatus.COMPLETED else transfer_info.updated_at,
            error_message=transfer_info.error_details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transfer status for {transfer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TransferInfo])
async def list_transfers(
    status: Optional[TransferStatus] = None,
    limit: int = 50
):
    """List all transfers, optionally filtered by status"""
    try:
        transfers = await livekit_service.list_transfers()
        
        # Filter by status if provided
        if status:
            transfers = [t for t in transfers if t.status == status]
        
        # Limit results
        transfers = transfers[:limit]
        
        # Convert to TransferInfo objects
        result = []
        for transfer in transfers:
            result.append(TransferInfo(
                transfer_id=transfer.transfer_id,
                original_room_id=transfer.original_room,
                consult_room_id=transfer.consult_room,
                target_room_id=transfer.target_room,
                caller_identity=transfer.participants.get("caller", ""),
                agent_a_identity=transfer.participants.get("agent_a", ""),
                agent_b_identity=transfer.participants.get("agent_b", ""),
                status=transfer.status,
                call_summary=transfer.call_summary,
                created_at=transfer.created_at,
                completed_at=None if transfer.status != TransferStatus.COMPLETED else transfer.updated_at,
                error_message=transfer.error_details
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to list transfers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{transfer_id}")
async def cancel_transfer(transfer_id: str):
    """Cancel an ongoing transfer"""
    try:
        transfer_info = await livekit_service.get_transfer_info(transfer_id)
        if not transfer_info:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        if transfer_info.status in [TransferStatus.COMPLETED, TransferStatus.CANCELLED]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel transfer in {transfer_info.status} status"
            )
        
        # Update status to cancelled
        transfer_info.status = TransferStatus.CANCELLED
        transfer_info.updated_at = datetime.now()
        transfer_info.steps_completed.append("transfer_cancelled")
        
        # Clean up consultation room if it exists
        try:
            await livekit_service.delete_room(transfer_info.consult_room)
        except Exception as e:
            logger.warning(f"Failed to delete consultation room {transfer_info.consult_room}: {e}")
        
        logger.info(f"Cancelled transfer {transfer_id}")
        
        return {
            "success": True,
            "message": f"Transfer {transfer_id} cancelled successfully",
            "transfer_id": transfer_id,
            "cancelled_at": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel transfer {transfer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def cleanup_transfer_resources(transfer_id: str):
    """Background task to clean up transfer resources"""
    try:
        transfer_info = await livekit_service.get_transfer_info(transfer_id)
        if transfer_info:
            # Additional cleanup logic can be added here
            logger.info(f"Cleaned up resources for transfer {transfer_id}")
    except Exception as e:
        logger.error(f"Failed to cleanup transfer resources for {transfer_id}: {e}")

@router.post("/agent-handoff/{transfer_id}")
async def agent_handoff(
    transfer_id: str,
    agent_a_identity: str,
    agent_b_identity: str
):
    """
    Handle the agent handoff process during warm transfer
    
    This endpoint:
    1. Removes Agent A from the original room
    2. Adds Agent B to the original room with the caller
    3. Provides new token for Agent B
    """
    try:
        # Get transfer information
        transfer_info = await livekit_service.get_transfer_info(transfer_id)
        if not transfer_info:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        # Generate new token for Agent B in the original room
        agent_b_token = await livekit_service.generate_join_token(
            room_id=transfer_info.original_room,
            identity=agent_b_identity,
            name=f"Agent B ({agent_b_identity})",
            role="agent_b"
        )
        
        # Remove Agent A from the original room
        await livekit_service.remove_participant(
            transfer_info.original_room,
            agent_a_identity
        )
        
        # Update transfer status
        transfer_info.status = TransferStatus.COMPLETED
        transfer_info.updated_at = datetime.now()
        transfer_info.steps_completed.append("agent_handoff_completed")
        
        logger.info(f"Agent handoff completed for transfer {transfer_id}")
        
        return {
            "success": True,
            "message": "Agent handoff completed successfully",
            "transfer_id": transfer_id,
            "agent_b_token": agent_b_token,
            "room_url": livekit_service.livekit_url,
            "original_room_id": transfer_info.original_room
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete agent handoff for transfer {transfer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
