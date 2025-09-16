"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Phone,
  MessageSquare,
  Users,
  Settings,
  Send,
  MoreVertical,
  Monitor,
  Grid3X3,
  Maximize2,
  Volume2,
  VolumeX,
  Copy,
  UserPlus,
  Shield,
  Clock,
  Wifi,
  Signal
} from "lucide-react";

interface ChatMessage {
  id: string;
  sender: string;
  message: string;
  timestamp: Date;
}

interface Participant {
  id: string;
  name: string;
  isVideoOn: boolean;
  isAudioOn: boolean;
  isSpeaking: boolean;
  joinedAt: Date;
}

export default function RoomPage() {
  const params = useParams();
  const roomCode = params.code as string;
  const [userName, setUserName] = useState("");
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isAudioOn, setIsAudioOn] = useState(true);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isParticipantsOpen, setIsParticipantsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [connectionQuality, setConnectionQuality] = useState<'excellent' | 'good' | 'poor'>('excellent');
  const [chatMessage, setChatMessage] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [meetingDuration, setMeetingDuration] = useState(0);

  useEffect(() => {
    // Get user name from localStorage
    const storedName = localStorage.getItem("userName");
    if (storedName) {
      setUserName(storedName);
      // Add current user as participant
      const currentUser: Participant = {
        id: "current-user",
        name: storedName,
        isVideoOn: true,
        isAudioOn: true,
        isSpeaking: false,
        joinedAt: new Date()
      };
      setParticipants([currentUser]);
    }

    // Add some demo participants
    const demoParticipants: Participant[] = [
      {
        id: "demo-1",
        name: "Alice Johnson",
        isVideoOn: true,
        isAudioOn: true,
        isSpeaking: false,
        joinedAt: new Date(Date.now() - 300000) // 5 minutes ago
      },
      {
        id: "demo-2",
        name: "Bob Smith",
        isVideoOn: false,
        isAudioOn: true,
        isSpeaking: true,
        joinedAt: new Date(Date.now() - 180000) // 3 minutes ago
      }
    ];

    // Add demo participants after a delay to simulate joining
    setTimeout(() => {
      setParticipants(prev => [...prev, ...demoParticipants]);
    }, 2000);

    // Add some demo chat messages
    setChatMessages([
      {
        id: "1",
        sender: "System",
        message: `Welcome to room ${roomCode}!`,
        timestamp: new Date()
      },
      {
        id: "2",
        sender: "Alice Johnson",
        message: "Hello everyone! Great to see you all here.",
        timestamp: new Date(Date.now() - 120000)
      },
      {
        id: "3",
        sender: "Bob Smith",
        message: "Hi Alice! Thanks for setting this up.",
        timestamp: new Date(Date.now() - 60000)
      }
    ]);

    // Start meeting timer
    const timer = setInterval(() => {
      setMeetingDuration(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [roomCode]);

  const toggleVideo = () => setIsVideoOn(!isVideoOn);
  const toggleAudio = () => setIsAudioOn(!isAudioOn);
  const toggleChat = () => setIsChatOpen(!isChatOpen);
  const toggleParticipants = () => setIsParticipantsOpen(!isParticipantsOpen);
  const toggleSettings = () => setIsSettingsOpen(!isSettingsOpen);
  const toggleScreenShare = () => setIsScreenSharing(!isScreenSharing);
  const toggleFullscreen = () => setIsFullscreen(!isFullscreen);

  const copyRoomCode = () => {
    navigator.clipboard.writeText(roomCode);
    toast.success("Room code copied!", {
      description: `Room code ${roomCode} has been copied to clipboard.`,
    });
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const sendMessage = () => {
    if (chatMessage.trim()) {
      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        sender: userName,
        message: chatMessage,
        timestamp: new Date()
      };
      setChatMessages([...chatMessages, newMessage]);
      setChatMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  };

  const leaveRoom = () => {
    window.location.href = "/";
  };

  return (
    <div className="h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Video className="h-6 w-6 text-blue-400" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-white font-semibold">Room {roomCode}</h1>
              <Button
                variant="ghost"
                size="sm"
                onClick={copyRoomCode}
                className="text-gray-400 hover:text-white p-1 h-6"
              >
                <Copy className="h-3 w-3" />
              </Button>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span>{participants.length} participant{participants.length !== 1 ? 's' : ''}</span>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{formatDuration(meetingDuration)}</span>
              </div>
              <div className="flex items-center gap-1">
                {connectionQuality === 'excellent' && <Signal className="h-3 w-3 text-green-400" />}
                {connectionQuality === 'good' && <Wifi className="h-3 w-3 text-yellow-400" />}
                {connectionQuality === 'poor' && <Wifi className="h-3 w-3 text-red-400" />}
                <span className="capitalize">{connectionQuality}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="bg-green-600 text-white flex items-center gap-1">
            <div className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></div>
            Live
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="text-gray-400 hover:text-white"
            onClick={toggleFullscreen}
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Video Area */}
        <div className="flex-1 relative bg-gray-900">
          {/* Main Video */}
          <div className="h-full flex items-center justify-center">
            <div className="relative w-full max-w-4xl aspect-video bg-gray-800 rounded-lg overflow-hidden">
              {isVideoOn ? (
                <div className="w-full h-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                  <div className="text-center text-white">
                    <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center mb-4 mx-auto">
                      <span className="text-2xl font-bold">{userName.charAt(0).toUpperCase()}</span>
                    </div>
                    <p className="text-lg font-medium">{userName}</p>
                    <p className="text-sm opacity-75">Camera is on</p>
                  </div>
                </div>
              ) : (
                <div className="w-full h-full bg-gray-700 flex items-center justify-center">
                  <div className="text-center text-gray-300">
                    <VideoOff className="w-16 h-16 mx-auto mb-4" />
                    <p className="text-lg font-medium">{userName}</p>
                    <p className="text-sm opacity-75">Camera is off</p>
                  </div>
                </div>
              )}
              
              {/* Audio indicator */}
              <div className="absolute bottom-4 left-4">
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                  isAudioOn ? 'bg-green-600' : 'bg-red-600'
                } text-white text-sm`}>
                  {isAudioOn ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                  <span>{userName}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Participant thumbnails */}
          <div className="absolute top-4 right-4 space-y-2 max-w-48">
            {participants.slice(1).map((participant) => (
              <div key={participant.id} className="relative w-32 h-24 bg-gray-700 rounded-lg overflow-hidden border-2 border-gray-600">
                {participant.isVideoOn ? (
                  <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                    <div className="text-center text-white">
                      <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center mb-1 mx-auto">
                        <span className="text-xs font-bold">{participant.name.charAt(0).toUpperCase()}</span>
                      </div>
                      <p className="text-xs font-medium truncate px-1">{participant.name}</p>
                    </div>
                  </div>
                ) : (
                  <div className="w-full h-full bg-gray-600 flex items-center justify-center">
                    <div className="text-center text-gray-300">
                      <VideoOff className="w-6 h-6 mx-auto mb-1" />
                      <p className="text-xs font-medium truncate px-1">{participant.name}</p>
                    </div>
                  </div>
                )}

                {/* Audio indicator */}
                <div className="absolute bottom-1 left-1">
                  <div className={`flex items-center justify-center w-5 h-5 rounded-full ${
                    participant.isAudioOn ? 'bg-green-600' : 'bg-red-600'
                  } text-white`}>
                    {participant.isAudioOn ? <Mic className="w-2.5 h-2.5" /> : <MicOff className="w-2.5 h-2.5" />}
                  </div>
                </div>

                {/* Speaking indicator */}
                {participant.isSpeaking && (
                  <div className="absolute inset-0 border-2 border-green-400 rounded-lg animate-pulse"></div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Participants Sidebar */}
        {isParticipantsOpen && (
          <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-blue-400" />
                  <h3 className="text-white font-medium">Participants</h3>
                  <Badge variant="secondary">
                    {participants.length}
                  </Badge>
                </div>
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  <UserPlus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {participants.map((participant) => (
                <div key={participant.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-700/50 hover:bg-gray-700">
                  <div className="relative">
                    <Avatar className="w-10 h-10">
                      <AvatarImage src="" />
                      <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white font-semibold">
                        {participant.name.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    {participant.isSpeaking && (
                      <div className="absolute inset-0 border-2 border-green-400 rounded-full animate-pulse"></div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-white font-medium truncate">{participant.name}</p>
                      {participant.id === "current-user" && (
                        <Badge variant="outline" className="text-xs">You</Badge>
                      )}
                    </div>
                    <p className="text-gray-400 text-xs">
                      Joined {participant.joinedAt.toLocaleTimeString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-1">
                    <div className={`p-1 rounded ${participant.isAudioOn ? 'text-green-400' : 'text-red-400'}`}>
                      {participant.isAudioOn ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                    </div>
                    <div className={`p-1 rounded ${participant.isVideoOn ? 'text-green-400' : 'text-red-400'}`}>
                      {participant.isVideoOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Settings Sidebar */}
        {isSettingsOpen && (
          <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-blue-400" />
                <h3 className="text-white font-medium">Settings</h3>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {/* Audio Settings */}
              <div className="space-y-3">
                <h4 className="text-white font-medium flex items-center gap-2">
                  <Volume2 className="h-4 w-4" />
                  Audio
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Microphone</span>
                    <Button variant="outline" size="sm" className="text-xs">
                      Test
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Speaker</span>
                    <Button variant="outline" size="sm" className="text-xs">
                      Test
                    </Button>
                  </div>
                </div>
              </div>

              {/* Video Settings */}
              <div className="space-y-3">
                <h4 className="text-white font-medium flex items-center gap-2">
                  <Video className="h-4 w-4" />
                  Video
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Camera</span>
                    <Button variant="outline" size="sm" className="text-xs">
                      Switch
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Quality</span>
                    <select className="bg-gray-700 text-white text-xs rounded px-2 py-1 border border-gray-600">
                      <option>HD</option>
                      <option>SD</option>
                      <option>Low</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* General Settings */}
              <div className="space-y-3">
                <h4 className="text-white font-medium flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  General
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Noise Cancellation</span>
                    <input type="checkbox" className="rounded" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Auto-adjust lighting</span>
                    <input type="checkbox" className="rounded" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300 text-sm">Show captions</span>
                    <input type="checkbox" className="rounded" />
                  </div>
                </div>
              </div>

              {/* Meeting Info */}
              <div className="space-y-3">
                <h4 className="text-white font-medium">Meeting Info</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">Room ID:</span>
                    <span className="text-white font-mono">{roomCode}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Duration:</span>
                    <span className="text-white">{formatDuration(meetingDuration)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Participants:</span>
                    <span className="text-white">{participants.length}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Chat Sidebar */}
        {isChatOpen && (
          <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-blue-400" />
                <h3 className="text-white font-medium">Chat</h3>
                <Badge variant="secondary" className="ml-auto">
                  {chatMessages.length}
                </Badge>
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {chatMessages.map((msg) => (
                <div key={msg.id} className="space-y-1">
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span className="font-medium">{msg.sender}</span>
                    <span>{msg.timestamp.toLocaleTimeString()}</span>
                  </div>
                  <div className="text-white text-sm bg-gray-700 rounded-lg px-3 py-2">
                    {msg.message}
                  </div>
                </div>
              ))}
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t border-gray-700">
              <div className="flex gap-2">
                <Input
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message..."
                  className="flex-1 bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                />
                <Button onClick={sendMessage} size="icon" className="bg-blue-600 hover:bg-blue-700">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Controls */}
      <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left side - Meeting info */}
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <div className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              <span>{formatDuration(meetingDuration)}</span>
            </div>
            <div className="flex items-center gap-1">
              {connectionQuality === 'excellent' && <Signal className="h-4 w-4 text-green-400" />}
              {connectionQuality === 'good' && <Wifi className="h-4 w-4 text-yellow-400" />}
              {connectionQuality === 'poor' && <Wifi className="h-4 w-4 text-red-400" />}
              <span className="capitalize">{connectionQuality}</span>
            </div>
          </div>

          {/* Center - Main controls */}
          <div className="flex items-center gap-3">
            <Button
              onClick={toggleAudio}
              variant={isAudioOn ? "default" : "destructive"}
              size="lg"
              className="rounded-full w-12 h-12"
              title={isAudioOn ? "Mute microphone" : "Unmute microphone"}
            >
              {isAudioOn ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
            </Button>

            <Button
              onClick={toggleVideo}
              variant={isVideoOn ? "default" : "destructive"}
              size="lg"
              className="rounded-full w-12 h-12"
              title={isVideoOn ? "Turn off camera" : "Turn on camera"}
            >
              {isVideoOn ? <Video className="h-5 w-5" /> : <VideoOff className="h-5 w-5" />}
            </Button>

            <Button
              onClick={toggleScreenShare}
              variant={isScreenSharing ? "secondary" : "outline"}
              size="lg"
              className="rounded-full w-12 h-12"
              title="Share screen"
            >
              <Monitor className="h-5 w-5" />
            </Button>

            <Button
              onClick={leaveRoom}
              variant="destructive"
              size="lg"
              className="rounded-full w-12 h-12 ml-4"
              title="Leave meeting"
            >
              <Phone className="h-5 w-5" />
            </Button>
          </div>

          {/* Right side - Additional controls */}
          <div className="flex items-center gap-2">
            <Button
              onClick={toggleParticipants}
              variant={isParticipantsOpen ? "secondary" : "outline"}
              size="lg"
              className="rounded-full w-12 h-12"
              title="Show participants"
            >
              <Users className="h-5 w-5" />
            </Button>

            <Button
              onClick={toggleChat}
              variant={isChatOpen ? "secondary" : "outline"}
              size="lg"
              className="rounded-full w-12 h-12 relative"
              title="Show chat"
            >
              <MessageSquare className="h-5 w-5" />
              {chatMessages.length > 1 && (
                <Badge className="absolute -top-1 -right-1 w-5 h-5 p-0 text-xs bg-red-500">
                  {chatMessages.length - 1}
                </Badge>
              )}
            </Button>

            <Button
              onClick={toggleSettings}
              variant={isSettingsOpen ? "secondary" : "outline"}
              size="lg"
              className="rounded-full w-12 h-12"
              title="Settings"
            >
              <Settings className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
