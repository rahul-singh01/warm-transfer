import { Room, RoomEvent, RemoteParticipant, LocalParticipant, Track } from 'livekit-client';

export interface LiveKitConfig {
  url: string;
  token: string;
}

export interface ParticipantInfo {
  identity: string;
  name: string;
  isLocal: boolean;
  isSpeaking: boolean;
  audioEnabled: boolean;
  videoEnabled: boolean;
  joinedAt: Date;
}

export interface TransferRequest {
  targetAgentId: string;
  callSummary?: string;
  roomId: string;
}

export interface CallSummary {
  id: string;
  content: string;
  duration: number;
  participantCount: number;
  keyPoints: string[];
  generatedAt: Date;
}

export class LiveKitManager {
  private room: Room | null = null;
  private isConnected = false;
  private participants: Map<string, ParticipantInfo> = new Map();
  private onParticipantUpdate?: (participants: ParticipantInfo[]) => void;
  private onConnectionStateChange?: (connected: boolean) => void;
  private onTranscriptUpdate?: (transcript: string, speaker: string) => void;

  constructor() {
    this.room = new Room();
    this.setupEventListeners();
  }

  private setupEventListeners() {
    if (!this.room) return;

    this.room.on(RoomEvent.Connected, () => {
      this.isConnected = true;
      this.onConnectionStateChange?.(true);
      console.log('Connected to LiveKit room');
    });

    this.room.on(RoomEvent.Disconnected, () => {
      this.isConnected = false;
      this.onConnectionStateChange?.(false);
      console.log('Disconnected from LiveKit room');
    });

    this.room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
      console.log('Participant connected:', participant.identity);
      this.updateParticipantInfo(participant);
    });

    this.room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
      console.log('Participant disconnected:', participant.identity);
      this.participants.delete(participant.identity);
      this.notifyParticipantUpdate();
    });

    this.room.on(RoomEvent.TrackMuted, (track: Track, participant: RemoteParticipant | LocalParticipant) => {
      this.updateParticipantInfo(participant);
    });

    this.room.on(RoomEvent.TrackUnmuted, (track: Track, participant: RemoteParticipant | LocalParticipant) => {
      this.updateParticipantInfo(participant);
    });

    this.room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      // Update speaking status for all participants
      this.participants.forEach((info, identity) => {
        info.isSpeaking = speakers.some(speaker => speaker.identity === identity);
      });
      this.notifyParticipantUpdate();
    });

    this.room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(payload));
        if (data.type === 'transcript') {
          this.onTranscriptUpdate?.(data.text, participant?.identity || 'Unknown');
        }
      } catch (error) {
        console.error('Error parsing data message:', error);
      }
    });
  }

  private updateParticipantInfo(participant: RemoteParticipant | LocalParticipant) {
    const info: ParticipantInfo = {
      identity: participant.identity,
      name: participant.name || participant.identity,
      isLocal: participant instanceof LocalParticipant,
      isSpeaking: false, // Will be updated by ActiveSpeakersChanged event
      audioEnabled: participant.isMicrophoneEnabled,
      videoEnabled: participant.isCameraEnabled,
      joinedAt: new Date(participant.joinedAt || Date.now())
    };

    this.participants.set(participant.identity, info);
    this.notifyParticipantUpdate();
  }

  private notifyParticipantUpdate() {
    const participantList = Array.from(this.participants.values());
    this.onParticipantUpdate?.(participantList);
  }

  async connect(config: LiveKitConfig): Promise<void> {
    if (!this.room) {
      throw new Error('Room not initialized');
    }

    try {
      await this.room.connect(config.url, config.token);
      
      // Add local participant info
      if (this.room.localParticipant) {
        this.updateParticipantInfo(this.room.localParticipant);
      }
    } catch (error) {
      console.error('Failed to connect to LiveKit room:', error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    if (this.room) {
      await this.room.disconnect();
      this.participants.clear();
      this.notifyParticipantUpdate();
    }
  }

  async enableMicrophone(enabled: boolean): Promise<void> {
    if (this.room?.localParticipant) {
      await this.room.localParticipant.setMicrophoneEnabled(enabled);
      this.updateParticipantInfo(this.room.localParticipant);
    }
  }

  async enableCamera(enabled: boolean): Promise<void> {
    if (this.room?.localParticipant) {
      await this.room.localParticipant.setCameraEnabled(enabled);
      this.updateParticipantInfo(this.room.localParticipant);
    }
  }

  async enableScreenShare(enabled: boolean): Promise<void> {
    if (this.room?.localParticipant) {
      await this.room.localParticipant.setScreenShareEnabled(enabled);
    }
  }

  sendMessage(message: string): void {
    if (this.room?.localParticipant) {
      const data = JSON.stringify({ type: 'chat', message, timestamp: Date.now() });
      this.room.localParticipant.publishData(new TextEncoder().encode(data), { reliable: true });
    }
  }

  // Event listener setters
  onParticipantsChanged(callback: (participants: ParticipantInfo[]) => void) {
    this.onParticipantUpdate = callback;
  }

  onConnectionChanged(callback: (connected: boolean) => void) {
    this.onConnectionStateChange = callback;
  }

  onTranscript(callback: (transcript: string, speaker: string) => void) {
    this.onTranscriptUpdate = callback;
  }

  // Getters
  get connected(): boolean {
    return this.isConnected;
  }

  get currentRoom(): Room | null {
    return this.room;
  }

  get participantList(): ParticipantInfo[] {
    return Array.from(this.participants.values());
  }
}

// API functions for backend communication
export async function createRoom(roomName: string): Promise<{ roomId: string; token: string }> {
  const response = await fetch('/api/rooms/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ roomName })
  });

  if (!response.ok) {
    throw new Error('Failed to create room');
  }

  return response.json();
}

export async function getJoinToken(roomId: string, identity: string, name: string): Promise<string> {
  const response = await fetch('/api/participants/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ roomId, identity, name })
  });

  if (!response.ok) {
    throw new Error('Failed to get join token');
  }

  const data = await response.json();
  return data.token;
}

export async function initiateTransfer(request: TransferRequest): Promise<{ consultRoomId: string; consultToken: string }> {
  const response = await fetch('/api/rooms/transfer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    throw new Error('Failed to initiate transfer');
  }

  return response.json();
}

export async function generateCallSummary(roomId: string): Promise<CallSummary> {
  const response = await fetch(`/api/calls/${roomId}/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!response.ok) {
    throw new Error('Failed to generate call summary');
  }

  return response.json();
}
