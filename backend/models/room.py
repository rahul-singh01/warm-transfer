from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class RoomType(str, Enum):
    CALL = "call"
    CONSULTATION = "consultation"
    TRANSFER = "transfer"

class ParticipantRole(str, Enum):
    CALLER = "caller"
    AGENT_A = "agent_a"
    AGENT_B = "agent_b"
    AI_AGENT = "ai_agent"

class TransferStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CreateRoomRequest(BaseModel):
    room_name: str
    room_type: RoomType = RoomType.CALL
    max_participants: int = 10

class CreateRoomResponse(BaseModel):
    room_id: str
    room_name: str
    room_type: RoomType
    created_at: datetime
    livekit_url: str

class JoinTokenRequest(BaseModel):
    room_id: str
    identity: str
    name: str
    role: ParticipantRole = ParticipantRole.CALLER
    metadata: Optional[Dict[str, Any]] = None

class JoinTokenResponse(BaseModel):
    token: str
    url: str
    room_id: str
    identity: str
    expires_at: datetime

class TransferRequest(BaseModel):
    room_id: str
    target_agent_id: str
    caller_identity: Optional[str] = None
    agent_a_identity: Optional[str] = None
    call_summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TransferResponse(BaseModel):
    transfer_id: str
    consult_room_id: str
    consult_token_agent_a: str
    consult_token_agent_b: str
    status: TransferStatus
    created_at: datetime

class CompleteConsultationRequest(BaseModel):
    agent_identity: str
    notes: Optional[str] = None

class CompleteConsultationResponse(BaseModel):
    success: bool
    message: str
    transfer_id: str
    completed_at: datetime

class CallSummaryRequest(BaseModel):
    room_id: str
    include_transcript: bool = True
    max_duration_minutes: Optional[int] = None

class CallSummaryResponse(BaseModel):
    summary_id: str
    room_id: str
    content: str
    key_points: List[str]
    duration_seconds: int
    participant_count: int
    generated_at: datetime
    transcript_included: bool

class ParticipantInfo(BaseModel):
    identity: str
    name: str
    role: ParticipantRole
    is_connected: bool
    joined_at: datetime
    audio_enabled: bool
    video_enabled: bool
    is_speaking: bool
    metadata: Optional[Dict[str, Any]] = None

class RoomInfo(BaseModel):
    room_id: str
    room_name: str
    room_type: RoomType
    created_at: datetime
    participants: List[ParticipantInfo]
    is_active: bool
    metadata: Optional[Dict[str, Any]] = None

class TransferInfo(BaseModel):
    transfer_id: str
    original_room_id: str
    consult_room_id: str
    target_room_id: Optional[str] = None
    caller_identity: str
    agent_a_identity: str
    agent_b_identity: str
    status: TransferStatus
    call_summary: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class HoldRequest(BaseModel):
    room_id: str
    participant_identity: str
    hold_music_url: Optional[str] = None

class HoldResponse(BaseModel):
    success: bool
    participant_identity: str
    is_on_hold: bool
    hold_started_at: Optional[datetime] = None

class TranscriptEntry(BaseModel):
    speaker_identity: str
    speaker_name: str
    text: str
    timestamp: datetime
    confidence: Optional[float] = None

class TranscriptResponse(BaseModel):
    room_id: str
    entries: List[TranscriptEntry]
    total_duration_seconds: int
    generated_at: datetime

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()

# Room state management models
class RoomState(BaseModel):
    room_id: str
    room_type: RoomType
    participants: Dict[str, ParticipantInfo]
    created_at: datetime
    last_activity: datetime
    is_active: bool
    metadata: Dict[str, Any] = {}

class TransferState(BaseModel):
    transfer_id: str
    status: TransferStatus
    original_room: str
    consult_room: str
    target_room: Optional[str] = None
    participants: Dict[str, str]  # role -> identity mapping
    created_at: datetime
    updated_at: datetime
    steps_completed: List[str] = []
    error_details: Optional[str] = None
