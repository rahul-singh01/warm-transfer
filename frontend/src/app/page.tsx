"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Video, Users, Shuffle } from "lucide-react";

export default function Home() {
  const [name, setName] = useState("");
  const [meetingId, setMeetingId] = useState("");
  const router = useRouter();

  const generateRandomId = () => {
    const randomId = Math.floor(1000 + Math.random() * 9000).toString();
    setMeetingId(randomId);
  };

  const handleJoinRoom = () => {
    if (!name.trim()) {
      alert("Please enter your name");
      return;
    }
    if (!meetingId.trim()) {
      alert("Please enter a meeting ID");
      return;
    }

    // Store name in localStorage for the room
    localStorage.setItem("userName", name);
    router.push(`/room/${meetingId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <Video className="h-12 w-12 text-blue-600 mr-2" />
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Warm Transfer System</h1>
          </div>
          <p className="text-gray-600 dark:text-gray-300">Talk with agents, get connected to the right person.</p>
        </div>

        <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm dark:bg-gray-800/80">
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2">
              <Users className="h-5 w-5" />
              Join Meeting
            </CardTitle>
            <CardDescription>
              Enter your details to join or create a meeting room
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">Your Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="Enter your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-12"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="meetingId">Meeting ID</Label>
              <div className="flex gap-2">
                <Input
                  id="meetingId"
                  type="text"
                  placeholder="Enter 4-digit meeting ID"
                  value={meetingId}
                  onChange={(e) => setMeetingId(e.target.value)}
                  maxLength={4}
                  className="h-12"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={generateRandomId}
                  className="h-12 w-12 shrink-0"
                  title="Generate random ID"
                >
                  <Shuffle className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <Button
              onClick={handleJoinRoom}
              className="w-full h-12 text-lg font-semibold bg-blue-600 hover:bg-blue-700"
              size="lg"
            >
              Join Room
            </Button>
          </CardContent>
        </Card>

        <div className="text-center mt-6 text-sm text-gray-500 dark:text-gray-400">
          <p>Powered by LiveKit • Secure & Private</p>
        </div>
      </div>
    </div>
  );
}
