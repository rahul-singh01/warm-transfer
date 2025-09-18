import { useState, useEffect, useRef, useCallback } from 'react';
import { LiveKitManager, ParticipantInfo, LiveKitConfig, TransferRequest, CallSummary } from '@/lib/livekit';
import { api } from '@/lib/api';

// Web Speech API types
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

declare var SpeechRecognition: {
  prototype: SpeechRecognition;
  new(): SpeechRecognition;
};

export interface UseLiveKitOptions {
  roomId?: string;
  identity?: string;
  name?: string;
  autoConnect?: boolean;
}

export interface UseLiveKitReturn {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  
  // Room access
  room: any; // LiveKit Room instance
  actualRoomId: string | null; // The actual room ID from backend
  
  // Participants
  participants: ParticipantInfo[];
  localParticipant: ParticipantInfo | null;
  
  // Media controls
  isMicrophoneEnabled: boolean;
  isCameraEnabled: boolean;
  isScreenSharing: boolean;
  
  // Transcript
  transcript: Array<{ speaker: string; text: string; timestamp: Date }>;
  
  // Transfer state
  isTransferring: boolean;
  transferError: string | null;
  
  // Actions
  connect: (config: LiveKitConfig) => Promise<void>;
  disconnect: () => Promise<void>;
  toggleMicrophone: () => Promise<void>;
  toggleCamera: () => Promise<void>;
  toggleScreenShare: () => Promise<void>;
  sendMessage: (message: string) => void;
  initiateTransfer: (targetAgentId: string) => Promise<{ consultRoomId: string; consultToken: string }>;
  generateSummary: () => Promise<CallSummary>;
  
  // Transcription
  isTranscribing: boolean;
  startTranscription: () => void;
  stopTranscription: () => void;

  // LiveKit manager instance
  manager: LiveKitManager | null;
}

export function useLiveKit(options: UseLiveKitOptions = {}): UseLiveKitReturn {
  const { roomId, identity, name, autoConnect = false } = options;
  
  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actualRoomId, setActualRoomId] = useState<string | null>(null); // Track the actual room ID from backend
  const [participants, setParticipants] = useState<ParticipantInfo[]>([]);
  const [isMicrophoneEnabled, setIsMicrophoneEnabled] = useState(false);
  const [isCameraEnabled, setIsCameraEnabled] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [transcript, setTranscript] = useState<Array<{ speaker: string; text: string; timestamp: Date }>>([]);
  const [isTransferring, setIsTransferring] = useState(false);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [speechRecognition, setSpeechRecognition] = useState<SpeechRecognition | null>(null);
  
  // Manager instance
  const managerRef = useRef<LiveKitManager | null>(null);
  
  // Initialize manager
  useEffect(() => {
    if (!managerRef.current) {
      managerRef.current = new LiveKitManager();
      
      // Set up event listeners
      managerRef.current.onConnectionChanged((connected) => {
        setIsConnected(connected);
        setIsConnecting(false);
        if (!connected) {
          setError(null);
        }
      });
      
      managerRef.current.onParticipantsChanged((participantList) => {
        setParticipants(participantList);
      });
      
      managerRef.current.onTranscript((text, speaker) => {
        setTranscript(prev => [...prev, {
          speaker,
          text,
          timestamp: new Date()
        }]);
      });
    }
    
    return () => {
      if (managerRef.current) {
        managerRef.current.disconnect();
      }
    };
  }, []);
  
  const connect = useCallback(async (config: LiveKitConfig) => {
    if (!managerRef.current) return;
    
    try {
      setIsConnecting(true);
      setError(null);
      await managerRef.current.connect(config);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setIsConnecting(false);
    }
  }, []);
  
  const handleAutoConnect = useCallback(async () => {
    if (!roomId || !identity || !name) return;
    
    try {
      setIsConnecting(true);
      setError(null);
      
      // Get join token from backend using API utility
      const response = await api.participants.getToken(roomId, identity, name) as {
        token: string;
        url: string;
        room_id: string;
        identity: string;
        expires_at: string;
      };
      
      // Store the actual room ID from the backend
      setActualRoomId(response.room_id);
      
      await connect({ url: response.url, token: response.token });
    } catch (err: any) {
      setError(err.message || 'Failed to auto-connect');
      setIsConnecting(false);
    }
  }, [roomId, identity, name, connect]);
  
  // Auto-connect if options provided  
  useEffect(() => {
    let mounted = true;
    
    if (autoConnect && roomId && identity && name && !isConnected && !isConnecting && mounted) {
      handleAutoConnect();
    }
    
    return () => {
      mounted = false;
    };
  }, [autoConnect, roomId, identity, name, isConnected, isConnecting, handleAutoConnect]);
  
  const disconnect = useCallback(async () => {
    if (!managerRef.current) return;
    
    try {
      await managerRef.current.disconnect();
      setTranscript([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnect failed');
    }
  }, []);
  
  const toggleMicrophone = useCallback(async () => {
    if (!managerRef.current) return;
    
    try {
      const newState = !isMicrophoneEnabled;
      await managerRef.current.enableMicrophone(newState);
      setIsMicrophoneEnabled(newState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle microphone');
    }
  }, [isMicrophoneEnabled]);
  
  const toggleCamera = useCallback(async () => {
    if (!managerRef.current) return;
    
    try {
      const newState = !isCameraEnabled;
      await managerRef.current.enableCamera(newState);
      setIsCameraEnabled(newState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle camera');
    }
  }, [isCameraEnabled]);
  
  const toggleScreenShare = useCallback(async () => {
    if (!managerRef.current) return;
    
    try {
      const newState = !isScreenSharing;
      await managerRef.current.enableScreenShare(newState);
      setIsScreenSharing(newState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle screen share');
    }
  }, [isScreenSharing]);
  
  const sendMessage = useCallback((message: string) => {
    if (!managerRef.current) return;
    managerRef.current.sendMessage(message);
  }, []);
  
  const initiateTransfer = useCallback(async (targetAgentId: string) => {
    if (!managerRef.current || !actualRoomId) {
      throw new Error('Not connected to a room');
    }
    
    try {
      setIsTransferring(true);
      setTransferError(null);
      
      const response = await api.rooms.transfer(targetAgentId, actualRoomId) as {
        consultRoomId: string;
        consultToken: string;
        transferId: string;
        status: string;
      };
      
      return response;
    } catch (err: any) {
      const errorMessage = err.message || 'Transfer failed';
      setTransferError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsTransferring(false);
    }
  }, [actualRoomId]);
  
  const generateSummary = useCallback(async (): Promise<CallSummary> => {
    if (!actualRoomId) {
      throw new Error('No active room');
    }
    
    try {
      const response = await api.calls.getSummary(actualRoomId) as CallSummary;
      return response;
    } catch (err: any) {
      const errorMessage = err.message || 'Summary generation failed';
      throw new Error(errorMessage);
    }
  }, [actualRoomId]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (SpeechRecognitionClass) {
        const recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
          setIsTranscribing(true);
        };

        recognition.onend = () => {
          setIsTranscribing(false);
        };

        recognition.onerror = (event) => {
          console.error('Speech recognition error:', event.error);
          setIsTranscribing(false);
        };

        recognition.onresult = (event) => {
          let finalTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const transcriptText = result[0].transcript;

            if (result.isFinal) {
              finalTranscript += transcriptText;
            }
          }

          if (finalTranscript) {
            const newEntry = {
              speaker: identity || 'You',
              text: finalTranscript.trim(),
              timestamp: new Date()
            };

            setTranscript(prev => [...prev, newEntry]);
          }
        };

        setSpeechRecognition(recognition);
      }
    }
  }, [identity]);

  // Start transcription
  const startTranscription = useCallback(() => {
    if (speechRecognition && !isTranscribing) {
      try {
        speechRecognition.start();
      } catch (error) {
        console.error('Failed to start speech recognition:', error);
      }
    }
  }, [speechRecognition, isTranscribing]);

  // Stop transcription
  const stopTranscription = useCallback(() => {
    if (speechRecognition && isTranscribing) {
      speechRecognition.stop();
    }
  }, [speechRecognition, isTranscribing]);

  // Get local participant
  const localParticipant = participants.find(p => p.isLocal) || null;
  
  return {
    // Connection state
    isConnected,
    isConnecting,
    error,
    
    // Room access
    room: managerRef.current?.currentRoom || null,
    actualRoomId,
    
    // Participants
    participants,
    localParticipant,
    
    // Media controls
    isMicrophoneEnabled,
    isCameraEnabled,
    isScreenSharing,
    
    // Transcript
    transcript,
    
    // Transfer state
    isTransferring,
    transferError,
    
    // Actions
    connect,
    disconnect,
    toggleMicrophone,
    toggleCamera,
    toggleScreenShare,
    sendMessage,
    initiateTransfer,
    generateSummary,

    // Transcription
    isTranscribing,
    startTranscription,
    stopTranscription,

    // Manager instance
    manager: managerRef.current
  };
}
