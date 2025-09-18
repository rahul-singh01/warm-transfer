# Warm Transfer System (LiveKit + LLMs)

A real-time call transfer system that enables agents to perform warm transfers with AI-generated call summaries, built on LiveKit's real-time communication platform.

## 🎯 Project Overview

This system allows Agent A to transfer a caller to Agent B with an AI-generated summary of the conversation, enabling seamless handoffs without requiring Agent B to listen to the entire call history.

### Key Features

- **Real-time Audio Communication**: LiveKit-powered voice calls
- **AI-Powered Summaries**: Automatic call summarization using LLMs
- **Warm Transfer Flow**: Private consultation between agents before transfer
- **Live Transcription**: Real-time speech-to-text during calls
- **Web-based Agent Console**: Modern UI for agents to manage calls

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   LiveKit       │
│   (Next.js)     │◄──►│   (Python)      │◄──►│   Server        │
│                 │    │                 │    │                 │
│ • Agent Console │    │ • Room Service  │    │ • Audio Rooms   │
│ • Transfer UI   │    │ • STT Pipeline  │    │ • Participants  │
│ • Live Transcript│    │ • LLM Summary   │   
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   External      │
                    │   Services      │
                    │                 │
                    │ • STT (Deepgram)│
                    │ • LLM (OpenAI)  │
                    │ • TTS (ElevenLabs)│
                    │ • PSTN (Twilio) │
                    └─────────────────┘
```

## 🚀 Implementation Approaches

### MVP (Recommended First)
- **On-demand summary generation** when transfer is initiated
- **Consult room** for private agent-to-agent communication
- **Simple participant movement** between rooms
- **Basic web interface** for agents

### Enhanced Version
- **Continuous micro-summaries** during the call
- **Instant transfer capability** with pre-generated context
- **Advanced transcript management** with search and history

## 🔄 Warm Transfer Flow

1. **Active Call**: Caller connected to Agent A in LiveKit room
2. **Transfer Initiation**: Agent A clicks "Transfer" button
3. **Caller Hold**: Caller placed on hold with music
4. **Consult Room**: Private room created for Agent A + Agent B
5. **AI Summary**: LLM generates call summary from transcript
6. **Summary Playback**: TTS plays summary to Agent B in consult room
7. **Agent Consultation**: Agents discuss privately (optional)
8. **Transfer Completion**: Agent B moved to caller's room, Agent A exits
9. **Call Continuation**: Agent B continues call with full context

## 🛠️ Technology Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **LiveKit Client SDK** - Real-time audio/video
- **Tailwind CSS** - Styling
- **TypeScript** - Type safety

### Backend
- **Python 3.11+** - Core backend language
- **FastAPI** - Modern async web framework
- **LiveKit Server SDK** - Room and participant management
- **LiveKit Agents** - Real-time audio processing

### External Services
- **LiveKit Cloud** - Real-time communication infrastructure
- **Deepgram/AssemblyAI** - Speech-to-text transcription
- **Groq** - Call summarization
- **Cartesia** - Text-to-speech synthesis
- **Twilio** - PSTN connectivity (optional)

## 📋 Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- API keys for chosen STT, LLM, and TTS providers

## 🚀 Quick Start

### 1. Setup API Keys

1. **LiveKit**: Get free API keys from [LiveKit Cloud](https://cloud.livekit.io)
2. **Deepgram(STT)**: Get free API keys from [Deepgram Cloud](https://console.deepgram.com/)
3. **Cartesia(TTS)**: Get free API keys from [Deepgram Cloud](https://play.cartesia.ai/)


### 3. Install Dependencies

```bash
# Install backend dependencies
cd backend
source venv/bin/activate
pip install fastapi uvicorn livekit-api python-dotenv openai

# Install frontend dependencies
cd ../frontend
npm install
```
