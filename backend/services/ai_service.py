import os
import asyncio
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from groq import Groq
import httpx

from models.room import TranscriptEntry, CallSummaryResponse

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.groq_api_key:
            logger.warning("GROQ_API_KEY not found, AI features will be limited")
        
        # Initialize Groq client
        if self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
        else:
            self.groq_client = None
    
    async def generate_call_summary(
        self, 
        transcript_entries: List[TranscriptEntry],
        room_id: str,
        context: Optional[str] = None
    ) -> CallSummaryResponse:
        """Generate a call summary using Groq LLM"""
        try:
            if not self.groq_client:
                raise ValueError("Groq API key not configured")
            
            # Prepare transcript text
            transcript_text = self._format_transcript(transcript_entries)
            
            if not transcript_text.strip():
                raise ValueError("No transcript content available")
            
            # Create prompt for call summary
            prompt = self._create_summary_prompt(transcript_text, context)
            
            # Generate summary using Groq
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast and currently supported model
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant specialized in creating concise, professional call summaries for customer service transfers. Focus on key issues, customer needs, and important context for the next agent."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
                top_p=1,
                stream=False
            )
            
            summary_content = response.choices[0].message.content
            
            # Extract key points from summary
            key_points = await self._extract_key_points(summary_content)
            
            # Calculate duration
            duration_seconds = self._calculate_duration(transcript_entries)
            
            return CallSummaryResponse(
                summary_id=f"summary_{room_id}_{int(datetime.now().timestamp())}",
                room_id=room_id,
                content=summary_content,
                key_points=key_points,
                duration_seconds=duration_seconds,
                participant_count=len(set(entry.speaker_identity for entry in transcript_entries)),
                generated_at=datetime.now(),
                transcript_included=True
            )
            
        except Exception as e:
            logger.error(f"Failed to generate call summary: {e}")
            raise
    
    async def generate_transfer_briefing(
        self,
        call_summary: str,
        agent_b_name: str,
        caller_name: str = "Customer",
        additional_context: Optional[str] = None
    ) -> str:
        """Generate a briefing for Agent B during warm transfer"""
        try:
            if not self.groq_client:
                raise ValueError("Groq API key not configured")
            
            prompt = f"""
            You are briefing {agent_b_name} about an incoming call transfer. 
            
            Call Summary:
            {call_summary}
            
            {f"Additional Context: {additional_context}" if additional_context else ""}
            
            Create a concise, professional briefing (2-3 sentences) that {agent_b_name} can quickly understand before taking over the call with {caller_name}. 
            Focus on:
            1. The main issue or request
            2. What has been discussed so far
            3. What the customer needs next
            
            Keep it conversational and helpful for a smooth handoff.
            """
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast model for real-time briefing
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant helping with call transfers. Create brief, clear summaries for agents."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=200,
                top_p=1,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate transfer briefing: {e}")
            raise
    
    async def _extract_key_points(self, summary_content: str) -> List[str]:
        """Extract key points from the summary"""
        try:
            if not self.groq_client:
                return []
            
            prompt = f"""
            Extract 3-5 key bullet points from this call summary:
            
            {summary_content}
            
            Return only the bullet points, one per line, starting with "•".
            """
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract key points from text as bullet points."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=300,
                top_p=1,
                stream=False
            )
            
            key_points_text = response.choices[0].message.content
            key_points = [
                point.strip().lstrip("•").strip() 
                for point in key_points_text.split("\n") 
                if point.strip() and "•" in point
            ]
            
            return key_points[:5]  # Limit to 5 points
            
        except Exception as e:
            logger.error(f"Failed to extract key points: {e}")
            return []
    
    def _format_transcript(self, transcript_entries: List[TranscriptEntry]) -> str:
        """Format transcript entries into readable text"""
        if not transcript_entries:
            return ""
        
        formatted_lines = []
        for entry in transcript_entries:
            timestamp = entry.timestamp.strftime("%H:%M:%S")
            formatted_lines.append(f"[{timestamp}] {entry.speaker_name}: {entry.text}")
        
        return "\n".join(formatted_lines)
    
    def _create_summary_prompt(self, transcript_text: str, context: Optional[str] = None) -> str:
        """Create a prompt for call summary generation"""
        prompt = f"""
        Please create a professional call summary based on this conversation transcript:

        {transcript_text}

        {f"Additional Context: {context}" if context else ""}

        Please provide:
        1. A brief overview of the call purpose
        2. Key issues or requests discussed
        3. Any resolutions or actions taken
        4. Important information for follow-up or transfer
        5. Customer sentiment and satisfaction level

        Keep the summary concise but comprehensive, suitable for agent handoff.
        """
        
        return prompt
    
    def _calculate_duration(self, transcript_entries: List[TranscriptEntry]) -> int:
        """Calculate call duration from transcript entries"""
        if not transcript_entries:
            return 0
        
        start_time = min(entry.timestamp for entry in transcript_entries)
        end_time = max(entry.timestamp for entry in transcript_entries)
        
        return int((end_time - start_time).total_seconds())

# Text-to-Speech Service
class TTSService:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
    async def text_to_speech(
        self, 
        text: str, 
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default ElevenLabs voice
        output_format: str = "mp3_44100_128"
    ) -> bytes:
        """Convert text to speech using ElevenLabs API"""
        try:
            logger.info(f"TTS request for text: {text[:100]}...")
            logger.info(f"ElevenLabs API key present: {bool(self.elevenlabs_api_key)}")
            
            if not self.elevenlabs_api_key or self.elevenlabs_api_key.strip() == "":
                # Fallback: return empty bytes (in production, use a different TTS service)
                logger.warning("ElevenLabs API key not configured, TTS disabled")
                return b""
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                return response.content
                
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            logger.error(f"Exception type: {type(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            return b""

# Global service instances
ai_service = AIService()
tts_service = TTSService()
