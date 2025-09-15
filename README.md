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
- **PSTN Integration**: Optional phone system connectivity via SIP

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   LiveKit       │
│   (Next.js)     │◄──►│   (Python)      │◄──►│   Server        │
│                 │    │                 │    │                 │
│ • Agent Console │    │ • Room Service  │    │ • Audio Rooms   │
│ • Transfer UI   │    │ • STT Pipeline  │    │ • Participants  │
│ • Live Transcript│    │ • LLM Summary   │    │ • SIP Gateway   │
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

### Enterprise Version
- **RAG-based call history** for deep context retrieval
- **Multi-channel handoff** (web → PSTN → legacy systems)
- **PII redaction** and compliance features
- **Advanced analytics** and reporting

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
- **OpenAI GPT-4** - Call summarization
- **ElevenLabs** - Text-to-speech synthesis
- **Twilio** - PSTN connectivity (optional)

## 📋 Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- API keys for chosen STT, LLM, and TTS providers

## 🚀 Quick Start

### 1. Setup API Keys

1. **LiveKit**: Get free API keys from [LiveKit Cloud](https://cloud.livekit.io)
2. **OpenAI**: Get API key from [OpenAI Platform](https://platform.openai.com)

### 2. Configuration

Edit `.env` file with your API keys:

```env
# LiveKit Configuration (Required)
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_secret_here
LIVEKIT_URL=wss://your-project.livekit.cloud

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_key_here
```

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

### 4. Run the Application

**Option A: Use the start script**
```bash
./start.sh
```

**Option B: Manual start**
```bash
# Terminal 1: Start backend
cd backend && source venv/bin/activate && python main.py

# Terminal 2: Start frontend
cd frontend && npm run dev
```

### 5. Access the Application

- **Agent Console**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

### 6. Test the System

1. Open two browser tabs to http://localhost:3000
2. In tab 1: Join as "Agent-A" in room "call-123"
3. In tab 2: Join as "Agent-B" in room "call-123"
4. In Agent-A tab: Add some transcript text and transfer to "Agent-B"
5. See the AI-generated summary in the alert!

## 📁 Project Structure

```
warm-transfer/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities and LiveKit setup
│   └── package.json
├── backend/                 # Python backend
│   ├── agents/              # LiveKit agents
│   ├── services/            # Business logic
│   ├── models/              # Data models
│   ├── routers/             # API routes
│   └── main.py              # FastAPI application
├── docs/                    # Documentation
└── README.md
```

## 🔧 Core APIs

### Room Management
- `POST /api/rooms/create` - Create new call room
- `POST /api/rooms/{room_id}/transfer` - Initiate warm transfer
- `DELETE /api/rooms/{room_id}` - End call and cleanup

### Participant Management
- `POST /api/participants/token` - Generate join token
- `PUT /api/participants/move` - Move participant between rooms
- `DELETE /api/participants/{identity}` - Remove participant

### Call Features
- `GET /api/calls/{call_id}/transcript` - Get call transcript
- `POST /api/calls/{call_id}/summary` - Generate AI summary
- `POST /api/calls/{call_id}/hold` - Place caller on hold

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
npm test

# Integration tests
npm run test:e2e
```

## 📖 Development Roadmap

### Phase 1: MVP (Week 1-2)
- [ ] Basic LiveKit room creation and joining
- [ ] Simple agent console UI
- [ ] Real-time transcription integration
- [ ] Basic transfer functionality
- [ ] AI summary generation

### Phase 2: Enhanced Features (Week 3-4)
- [ ] Improved UI/UX for agent console
- [ ] Hold music and better call management
- [ ] Continuous summary updates
- [ ] Error handling and fallbacks
- [ ] Basic analytics

### Phase 3: Production Ready (Week 5-6)
- [ ] PSTN integration via SIP
- [ ] Security and compliance features
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Deployment automation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder for detailed guides
- **Issues**: Report bugs and request features via GitHub Issues
- **LiveKit Docs**: https://docs.livekit.io/
- **Community**: Join the LiveKit Discord for real-time help

---

**Next Steps**: Ready to start implementation? Begin with the MVP approach and follow the development roadmap above.
