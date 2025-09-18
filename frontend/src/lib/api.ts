/**
 * API utility for communicating with the backend server
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiError {
  message: string;
  status: number;
  details?: any;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorDetails;

      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
        errorDetails = errorData;
      } catch {
        // If we can't parse JSON, use the default error message
      }

      const error: ApiError = {
        message: errorMessage,
        status: response.status,
        details: errorDetails
      };
      
      throw error;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }
    
    // Return empty object for successful responses without JSON content
    return {} as T;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      console.log(`API Request: ${config.method || 'GET'} ${url}`);
      const response = await fetch(url, config);
      return this.handleResponse<T>(response);
    } catch (error) {
      console.error(`API Error for ${url}:`, error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    return this.request('/api/health');
  }

  // Room management
  async createRoom(data: {
    room_name: string;
    room_type?: string;
    max_participants?: number;
  }) {
    return this.request('/api/rooms/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listRooms() {
    return this.request('/api/rooms/');
  }

  async findRoomByName(roomName: string) {
    const rooms = await this.listRooms() as Array<{
      room_id: string;
      room_name: string;
      room_type: string;
      created_at: string;
      participants: any[];
      is_active: boolean;
      metadata: any;
    }>;
    
    return rooms.find(room => room.room_name === roomName && room.is_active);
  }

  async transferCall(data: {
    targetAgentId: string;
    roomId: string;
    callSummary?: string;
  }) {
    return this.request('/api/rooms/transfer', {
      method: 'POST',
      body: JSON.stringify({
        room_id: data.roomId,
        target_agent_id: data.targetAgentId,
        call_summary: data.callSummary
      }),
    });
  }

  async completeConsultation(transferId: string, agentIdentity: string) {
    return this.request(`/api/rooms/transfer/${transferId}/complete-consultation`, {
      method: 'POST',
      body: JSON.stringify({
        agent_identity: agentIdentity
      }),
    });
  }

  // Participant management
  async generateJoinToken(data: {
    room_id: string;
    identity: string;
    name: string;
    role?: string;
    metadata?: any;
  }) {
    return this.request('/api/participants/token', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async removeParticipant(identity: string, roomId: string) {
    return this.request(`/api/participants/${identity}?room_id=${roomId}`, {
      method: 'DELETE',
    });
  }

  // Call management
  async generateCallSummary(callId: string) {
    return this.request(`/api/calls/${callId}/summary`, {
      method: 'POST',
    });
  }

  async getCallTranscript(callId: string) {
    return this.request(`/api/calls/${callId}/transcript`);
  }

  async holdCall(callId: string, hold: boolean = true) {
    return this.request(`/api/calls/${callId}/hold`, {
      method: 'POST',
      body: JSON.stringify({ hold }),
    });
  }
}

// Create a singleton instance
export const apiClient = new ApiClient();

// Export types
export type { ApiError };

// Utility functions for common API operations
export const api = {
  // Health check
  health: () => apiClient.healthCheck(),

  // Room operations
  rooms: {
    create: (roomName: string, options?: { roomType?: string; maxParticipants?: number }) =>
      apiClient.createRoom({
        room_name: roomName,
        room_type: options?.roomType || 'call',
        max_participants: options?.maxParticipants || 10,
      }),
    
    list: () => apiClient.listRooms(),
    
    findByName: (roomName: string) => apiClient.findRoomByName(roomName),
    
    transfer: (targetAgentId: string, roomId: string, callSummary?: string) =>
      apiClient.transferCall({ targetAgentId, roomId, callSummary }),
    
    completeConsultation: (transferId: string, agentIdentity: string) =>
      apiClient.completeConsultation(transferId, agentIdentity),
  },

  // Participant operations
  participants: {
    getToken: (roomId: string, identity: string, name: string, options?: { role?: string; metadata?: any }) =>
      apiClient.generateJoinToken({
        room_id: roomId,
        identity,
        name,
        role: options?.role || 'caller',
        metadata: options?.metadata,
      }),
    
    remove: (identity: string, roomId: string) =>
      apiClient.removeParticipant(identity, roomId),
  },

  // Call operations
  calls: {
    getSummary: (callId: string) => apiClient.generateCallSummary(callId),
    getTranscript: (callId: string) => apiClient.getCallTranscript(callId),
    hold: (callId: string, hold: boolean = true) => apiClient.holdCall(callId, hold),
  },
};

export default api;
