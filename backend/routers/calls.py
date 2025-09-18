from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from models.room import (
    CallSummaryRequest, CallSummaryResponse,
    TranscriptResponse, TranscriptEntry,
    ErrorResponse
)
from services.ai_service import ai_service
from services.livekit_service import livekit_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calls", tags=["calls"])

@router.post("/{room_id}/summary", response_model=CallSummaryResponse)
async def generate_call_summary(room_id: str, request: CallSummaryRequest = None):
    """Generate AI-powered call summary"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        # Get transcript entries (in production, this would come from a database)
        transcript_entries = await get_room_transcript(room_id)
        
        if not transcript_entries:
            # Create mock transcript for demonstration
            transcript_entries = create_mock_transcript(room_id)
        
        # Generate summary using AI service
        summary_response = await ai_service.generate_call_summary(
            transcript_entries=transcript_entries,
            room_id=room_id,
            context="Call summary for warm transfer"
        )
        
        logger.info(f"Generated call summary for room {room_id}")
        return summary_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate call summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}/transcript", response_model=TranscriptResponse)
async def get_call_transcript(room_id: str, include_timestamps: bool = True):
    """Get call transcript"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        # Get transcript entries
        transcript_entries = await get_room_transcript(room_id)
        
        if not transcript_entries:
            # Create mock transcript for demonstration
            transcript_entries = create_mock_transcript(room_id)
        
        # Calculate total duration
        if transcript_entries:
            start_time = min(entry.timestamp for entry in transcript_entries)
            end_time = max(entry.timestamp for entry in transcript_entries)
            total_duration = int((end_time - start_time).total_seconds())
        else:
            total_duration = 0
        
        return TranscriptResponse(
            room_id=room_id,
            entries=transcript_entries,
            total_duration_seconds=total_duration,
            generated_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{room_id}/briefing")
async def generate_transfer_briefing(
    room_id: str,
    agent_b_name: str,
    caller_name: str = "Customer",
    additional_context: Optional[str] = None
):
    """Generate a briefing for Agent B during warm transfer"""
    try:
        # Get call summary first
        summary_request = CallSummaryRequest(room_id=room_id)
        summary_response = await generate_call_summary(room_id, summary_request)
        
        # Generate briefing
        briefing = await ai_service.generate_transfer_briefing(
            call_summary=summary_response.content,
            agent_b_name=agent_b_name,
            caller_name=caller_name,
            additional_context=additional_context
        )
        
        return {
            "briefing": briefing,
            "summary_id": summary_response.summary_id,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{room_id}/start-recording")
async def start_call_recording(room_id: str):
    """Start recording a call (placeholder)"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        # TODO: Implement actual recording start
        logger.info(f"Started recording for room {room_id}")
        
        return {
            "success": True,
            "message": f"Recording started for room {room_id}",
            "started_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{room_id}/stop-recording")
async def stop_call_recording(room_id: str):
    """Stop recording a call (placeholder)"""
    try:
        # Validate that the room exists
        room_info = await livekit_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
        
        # TODO: Implement actual recording stop
        logger.info(f"Stopped recording for room {room_id}")
        
        return {
            "success": True,
            "message": f"Recording stopped for room {room_id}",
            "stopped_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def get_room_transcript(room_id: str) -> List[TranscriptEntry]:
    """Get transcript entries for a room (placeholder)"""
    # In production, this would fetch from a database
    # For now, return empty list (will use mock data)
    return []