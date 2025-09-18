"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  VideoTrack,
  useParticipants,
  useRoomContext,
  useLocalParticipant,
} from "@livekit/components-react";
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Phone,
  Users,
  Settings,
  Clock,
} from "lucide-react";
import { api } from "@/lib/api";

export default function RoomPage() {
  const params = useParams();
  const roomCode = params.code as string;
  const [userName, setUserName] = useState("");
  const [connectionDetails, setConnectionDetails] = useState<{
    wsUrl?: string;
    token?: string;
    shouldConnect: boolean;
  }>({ shouldConnect: false });
  const [meetingDuration, setMeetingDuration] = useState(0);
  const [userIdentity] = useState(() => `user_${Date.now()}`);

  useEffect(() => {
    const storedName = localStorage.getItem("userName");
    if (storedName) setUserName(storedName);

    const timer = setInterval(() => setMeetingDuration((prev) => prev + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const connectToRoom = async () => {
      if (userName && !connectionDetails.shouldConnect) {
        try {
          let actualRoomId = roomCode;

          try {
            const existingRoom = await api.rooms.findByName(roomCode);
            if (existingRoom) {
              actualRoomId = existingRoom.room_id;
            } else {
              const createResponse = await api.rooms.create(roomCode, {
                roomType: "call",
                maxParticipants: 10,
              });
              actualRoomId = createResponse.room_id;
              toast.success("Room created successfully");
            }
          } catch (roomError) {
            console.error("Error managing room:", roomError);
            actualRoomId = roomCode;
          }

          const response = await api.participants.getToken(
            actualRoomId,
            userIdentity,
            userName
          );

          if (!process.env.NEXT_PUBLIC_LIVEKIT_URL) {
            throw new Error("NEXT_PUBLIC_LIVEKIT_URL is not set");
          }

          setConnectionDetails({
            wsUrl: process.env.NEXT_PUBLIC_LIVEKIT_URL,
            token: response.token,
            shouldConnect: true,
          });
        } catch (error) {
          console.error("Failed to connect to room:", error);
          toast.error("Failed to connect to room");
        }
      }
    };

    connectToRoom();
  }, [userName, roomCode, userIdentity, connectionDetails.shouldConnect]);

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return hours > 0
      ? `${hours}:${minutes.toString().padStart(2, "0")}:${secs
          .toString()
          .padStart(2, "0")}`
      : `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  const leaveRoom = () => {
    setConnectionDetails({ shouldConnect: false });
    window.location.href = "/";
  };

  if (!connectionDetails.shouldConnect || !connectionDetails.token) {
    return (
      <div className="h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white mb-4 mx-auto"></div>
          <p className="text-lg">Connecting to room...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-900 flex flex-col">
      <LiveKitRoom
        className="flex flex-col h-full"
        serverUrl={connectionDetails.wsUrl}
        token={connectionDetails.token}
        connect={connectionDetails.shouldConnect}
        onError={(e) => {
          toast.error("Connection error: " + e.message);
          console.error(e);
        }}
        onConnected={() => toast.success("Connected to room")}
        onDisconnected={() => toast.info("Disconnected from room")}
      >
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Video className="h-6 w-6 text-blue-400" />
            <div>
              <h1 className="text-white font-semibold">Room {roomCode}</h1>
              <div className="flex items-center gap-4 text-sm text-gray-400">
                <RoomInfo />
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatDuration(meetingDuration)}</span>
                </div>
              </div>
            </div>
          </div>
          <Badge
            variant="secondary"
            className="bg-green-600 text-white flex items-center gap-1"
          >
            <div className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></div>
            Live
          </Badge>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex">
          <div className="flex-1 relative bg-gray-900">
            <VideoArea userName={userName} />
          </div>
        </div>

        {/* Bottom Controls */}
        <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
          <BottomControls onLeaveRoom={leaveRoom} />
        </div>

        {/* Handle audio playback */}
        <RoomAudioRenderer />
        <StartAudio label="Click to enable audio playback" />
      </LiveKitRoom>
    </div>
  );
}

function RoomInfo() {
  const participants = useParticipants();
  const room = useRoomContext();

  return (
    <>
      <span>
        {participants.length} participant{participants.length !== 1 ? "s" : ""}
      </span>
      <div className="flex items-center gap-1">
        {room && <div className="w-2 h-2 bg-green-400 rounded-full"></div>}
        <span>Connected</span>
      </div>
    </>
  );
}

function VideoArea({ userName }: { userName: string }) {
  const participants = useParticipants();
  const localParticipant = participants.find((p) => p.isLocal);

  // Get the camera track reference
  const cameraTrack = localParticipant?.getTrackPublication('camera')?.track;
  const hasCameraTrack = localParticipant?.isCameraEnabled && cameraTrack;

  return (
    <div className="h-full flex items-center justify-center">
      <div className="relative w-full max-w-4xl aspect-video bg-gray-800 rounded-lg overflow-hidden">
        {hasCameraTrack ? (
          <VideoTrack
            trackRef={{
              participant: localParticipant,
              publication: localParticipant.getTrackPublication('camera')!,
              source: 'camera'
            }}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <div className="text-center text-white">
              <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center mb-4 mx-auto">
                <span className="text-2xl font-bold">
                  {userName.charAt(0).toUpperCase()}
                </span>
              </div>
              <p className="text-lg font-medium">{userName}</p>
              <p className="text-sm opacity-75">Camera is off</p>
            </div>
          </div>
        )}

        {/* Remote participant thumbnails */}
        <div className="absolute top-4 right-4 space-y-2 max-w-48">
          {participants
            .filter((p) => !p.isLocal)
            .map((participant) => {
              const remoteCameraTrack = participant.getTrackPublication('camera');
              const hasRemoteCamera = participant.isCameraEnabled && remoteCameraTrack?.track;
              
              return (
                <div
                  key={participant.identity}
                  className="relative w-32 h-24 bg-gray-700 rounded-lg overflow-hidden border-2 border-gray-600"
                >
                  {hasRemoteCamera ? (
                    <VideoTrack
                      trackRef={{
                        participant,
                        publication: remoteCameraTrack!,
                        source: 'camera'
                      }}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                      <div className="text-center text-white">
                        <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center mb-1 mx-auto">
                          <span className="text-xs font-bold">
                            {participant.name?.charAt(0).toUpperCase() || "A"}
                          </span>
                        </div>
                        <p className="text-xs font-medium truncate px-1">
                          {participant.name || "Agent"}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}

function BottomControls({ onLeaveRoom }: { onLeaveRoom: () => void }) {
  const { localParticipant } = useLocalParticipant();
  
  // Use the actual state from LiveKit
  const isCameraEnabled = localParticipant?.isCameraEnabled ?? false;
  const isMicrophoneEnabled = localParticipant?.isMicrophoneEnabled ?? false;

  const toggleCamera = async () => {
    if (localParticipant) {
      await localParticipant.setCameraEnabled(!isCameraEnabled);
    }
  };

  const toggleMic = async () => {
    if (localParticipant) {
      await localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
    }
  };

  return (
    <div className="flex items-center justify-center">
      <div className="flex items-center gap-4">
        {/* Mic toggle */}
        <Button
          variant={isMicrophoneEnabled ? "secondary" : "destructive"}
          size="lg"
          className="rounded-full w-12 h-12"
          onClick={toggleMic}
          title={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
        >
          {isMicrophoneEnabled ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
        </Button>

        {/* Camera toggle */}
        <Button
          variant={isCameraEnabled ? "secondary" : "destructive"}
          size="lg"
          className="rounded-full w-12 h-12"
          onClick={toggleCamera}
          title={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
        >
          {isCameraEnabled ? (
            <Video className="h-5 w-5" />
          ) : (
            <VideoOff className="h-5 w-5" />
          )}
        </Button>

        {/* Leave button */}
        <Button
          variant="destructive"
          size="lg"
          className="rounded-full w-12 h-12"
          onClick={onLeaveRoom}
          title="Leave meeting"
        >
          <Phone className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}