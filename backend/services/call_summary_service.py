import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import aiohttp
import json

from models.room import (
    CallSummaryResponse, TranscriptEntry, TranscriptResponse
)

logger = logging.getLogger(__name__)

class CallSummaryService:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # In-memory storage for call transcripts and summaries
        self.transcripts: Dict[str, List[TranscriptEntry]] = {}
        self.summaries: Dict[str, CallSummaryResponse] = {}
    
    async def add_transcript_entry(
        self,
        room_id: str,
        speaker_identity: str,
        speaker_name: str,
        text: str,
        confidence: Optional[float] = None
    ):
        """Add a transcript entry for a room"""
        try:
            if room_id not in self.transcripts:
                self.transcripts[room_id] = []
            
            entry = TranscriptEntry(
                speaker_identity=speaker_identity,
                speaker_name=speaker_name,
                text=text,
                timestamp=datetime.now(),
                confidence=confidence
            )
            
            self.transcripts[room_id].append(entry)
            logger.debug(f"Added transcript entry for room {room_id}: {speaker_name}: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to add transcript entry for room {room_id}: {e}")
    
    async def get_transcript(self, room_id: str) -> Optional[TranscriptResponse]:
        """Get the transcript for a room"""
        try:
            if room_id not in self.transcripts:
                return None
            
            entries = self.transcripts[room_id]
            if not entries:
                return None
            
            # Calculate total duration
            if len(entries) > 1:
                start_time = entries[0].timestamp
                end_time = entries[-1].timestamp
                duration_seconds = int((end_time - start_time).total_seconds())
            else:
                duration_seconds = 0
            
            return TranscriptResponse(
                room_id=room_id,
                entries=entries,
                total_duration_seconds=duration_seconds,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get transcript for room {room_id}: {e}")
            return None
    
    async def generate_summary(
        self,
        room_id: str,
        include_transcript: bool = True,
        max_duration_minutes: Optional[int] = None
    ) -> CallSummaryResponse:
        """Generate an AI-powered call summary"""
        try:
            summary_id = f"summary_{uuid.uuid4().hex[:8]}"
            
            # Get transcript if available
            transcript = await self.get_transcript(room_id) if include_transcript else None
            
            # Filter transcript by duration if specified
            transcript_text = ""
            key_points = []
            duration_seconds = 0
            participant_count = 0
            
            if transcript and transcript.entries:
                entries = transcript.entries
                
                # Filter by max duration if specified
                if max_duration_minutes:
                    cutoff_time = datetime.now() - timedelta(minutes=max_duration_minutes)
                    entries = [e for e in entries if e.timestamp >= cutoff_time]
                
                # Build transcript text
                transcript_lines = []
                speakers = set()
                
                for entry in entries:
                    speakers.add(entry.speaker_identity)
                    timestamp_str = entry.timestamp.strftime("%H:%M:%S")
                    transcript_lines.append(f"[{timestamp_str}] {entry.speaker_name}: {entry.text}")
                
                transcript_text = "\n".join(transcript_lines)
                participant_count = len(speakers)
                duration_seconds = transcript.total_duration_seconds
                
                # Generate AI summary if we have transcript and API key
                if transcript_text and self.groq_api_key:
                    ai_summary, ai_key_points = await self._generate_ai_summary(transcript_text)
                    if ai_summary:
                        summary_content = ai_summary
                        key_points = ai_key_points
                    else:
                        summary_content = self._generate_basic_summary(transcript_text, speakers)
                        key_points = self._extract_basic_key_points(transcript_text)
                else:
                    summary_content = self._generate_basic_summary(transcript_text, speakers)
                    key_points = self._extract_basic_key_points(transcript_text)
            else:
                # No transcript available
                summary_content = f"Call summary for room {room_id}. No transcript available."
                key_points = ["No transcript data available for analysis"]
                participant_count = 0
                duration_seconds = 0
            
            # Create summary response
            summary = CallSummaryResponse(
                summary_id=summary_id,
                room_id=room_id,
                content=summary_content,
                key_points=key_points,
                duration_seconds=duration_seconds,
                participant_count=participant_count,
                generated_at=datetime.now(),
                transcript_included=include_transcript and transcript is not None
            )
            
            # Store summary
            self.summaries[summary_id] = summary
            
            logger.info(f"Generated call summary {summary_id} for room {room_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate call summary for room {room_id}: {e}")
            # Return a basic summary even if generation fails
            return CallSummaryResponse(
                summary_id=f"error_{uuid.uuid4().hex[:8]}",
                room_id=room_id,
                content=f"Error generating summary for room {room_id}: {str(e)}",
                key_points=["Summary generation failed"],
                duration_seconds=0,
                participant_count=0,
                generated_at=datetime.now(),
                transcript_included=False
            )
    
    async def _generate_ai_summary(self, transcript_text: str) -> tuple[Optional[str], List[str]]:
        """Generate AI-powered summary using Groq API"""
        try:
            if not self.groq_api_key:
                logger.warning("No Groq API key available for AI summary generation")
                return None, []
            
            prompt = f"""
            Please analyze the following call transcript and provide:
            1. A concise summary (2-3 sentences) of the main conversation
            2. Key points or topics discussed (3-5 bullet points)
            
            Transcript:
            {transcript_text}
            
            Please format your response as JSON with 'summary' and 'key_points' fields.
            """
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes call transcripts and provides concise summaries and key points. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.groq_api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        
                        # Try to parse JSON response
                        try:
                            parsed = json.loads(content)
                            summary = parsed.get("summary", "")
                            key_points = parsed.get("key_points", [])
                            
                            if isinstance(key_points, str):
                                key_points = [key_points]
                            
                            return summary, key_points
                        except json.JSONDecodeError:
                            # Fallback: use the raw content as summary
                            return content, [content]
                    else:
                        logger.error(f"Groq API error: {response.status} - {await response.text()}")
                        return None, []
            
        except Exception as e:
            logger.error(f"Failed to generate AI summary: {e}")
            return None, []
    
    def _generate_basic_summary(self, transcript_text: str, speakers: set) -> str:
        """Generate a basic summary without AI"""
        if not transcript_text:
            return "No conversation content available for summary."
        
        lines = transcript_text.split('\n')
        total_lines = len(lines)
        speaker_count = len(speakers)
        
        # Extract first and last few lines for context
        preview_lines = lines[:3] if len(lines) >= 3 else lines
        
        summary = f"Call involved {speaker_count} participants with {total_lines} exchanges. "
        
        if preview_lines:
            summary += f"Conversation started with: {preview_lines[0].split('] ', 1)[-1] if '] ' in preview_lines[0] else preview_lines[0]}"
        
        return summary
    
    def _extract_basic_key_points(self, transcript_text: str) -> List[str]:
        """Extract basic key points without AI"""
        if not transcript_text:
            return ["No conversation content available"]
        
        lines = transcript_text.split('\n')
        
        key_points = [
            f"Total conversation length: {len(lines)} exchanges",
            f"Conversation duration: {len(lines) * 10} seconds (estimated)",
        ]
        
        # Look for question marks (potential questions/issues)
        questions = [line for line in lines if '?' in line]
        if questions:
            key_points.append(f"Questions or issues raised: {len(questions)}")
        
        # Look for common keywords
        important_keywords = ['problem', 'issue', 'help', 'support', 'transfer', 'escalate']
        keyword_mentions = []
        
        for keyword in important_keywords:
            if any(keyword.lower() in line.lower() for line in lines):
                keyword_mentions.append(keyword)
        
        if keyword_mentions:
            key_points.append(f"Key topics mentioned: {', '.join(keyword_mentions)}")
        
        return key_points[:5]  # Limit to 5 key points
    
    async def get_summary(self, summary_id: str) -> Optional[CallSummaryResponse]:
        """Get a previously generated summary"""
        return self.summaries.get(summary_id)
    
    async def list_summaries(self, room_id: Optional[str] = None) -> List[CallSummaryResponse]:
        """List all summaries, optionally filtered by room_id"""
        summaries = list(self.summaries.values())
        
        if room_id:
            summaries = [s for s in summaries if s.room_id == room_id]
        
        return summaries
    
    async def cleanup_old_data(self, max_age_hours: int = 24) -> int:
        """Clean up old transcripts and summaries"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        # Clean up old transcripts
        rooms_to_remove = []
        for room_id, entries in self.transcripts.items():
            if entries and entries[-1].timestamp < cutoff_time:
                rooms_to_remove.append(room_id)
        
        for room_id in rooms_to_remove:
            del self.transcripts[room_id]
            cleaned_count += 1
        
        # Clean up old summaries
        summaries_to_remove = []
        for summary_id, summary in self.summaries.items():
            if summary.generated_at < cutoff_time:
                summaries_to_remove.append(summary_id)
        
        for summary_id in summaries_to_remove:
            del self.summaries[summary_id]
            cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old transcript/summary records")
        return cleaned_count

# Global service instance
call_summary_service = CallSummaryService()
