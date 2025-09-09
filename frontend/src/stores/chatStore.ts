import { create } from 'zustand';
import { sendChat, getChat, listChats, resetChat } from '../api';
import { API_BASE } from '../api';
import { flushSync } from 'react-dom';

export interface ChatState {
  // Chat content state
  messages: any[];
  input: string;
  sending: boolean;
  error: string | null;

  // Session management
  sessionId: string;
  availableSessions: string[];

  // Circuit integration
  selectedCircuitId: number | null;

  // Actions
  setMessages: (messages: any[] | ((prev: any[]) => any[])) => void;
  setInput: (input: string) => void;
  setSending: (sending: boolean) => void;
  setError: (error: string | null) => void;
  setSessionId: (sessionId: string) => void;
  setAvailableSessions: (sessions: string[]) => void;
  setSelectedCircuitId: (circuitId: number | null) => void;

  // Async actions
  sendMessage: (message: string) => Promise<string>;
  loadChat: (sessionId: string) => Promise<void>;
  loadSessions: () => Promise<void>;
  resetChatSession: (sessionId: string) => Promise<void>;
  createNewSession: (sessionName: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  messages: [],
  input: '',
  sending: false,
  error: null,
  sessionId: 'default',
  availableSessions: ['default'],
  selectedCircuitId: null,

  // Basic setters
  setMessages: (messages) => set((state) => ({ messages: typeof messages === 'function' ? messages(state.messages) : messages })),
  setInput: (input) => set({ input }),
  setSending: (sending) => set({ sending }),
  setError: (error) => set({ error }),
  setSessionId: (sessionId) => set({ sessionId }),
  setAvailableSessions: (availableSessions) => set({ availableSessions }),
  setSelectedCircuitId: (selectedCircuitId) => set({ selectedCircuitId }),

  // Async actions
  sendMessage: async (message: string) => {
    if (!message.trim() || get().sending) return '';

    const { sessionId, messages, selectedCircuitId } = get();
    const userMsg = { role: 'user', content: message.trim() };

    set({ sending: true, error: null });

      let circuitOutputs = null;
      if (selectedCircuitId) {
        // Execute circuit with message as input
        try {
          const res = await fetch(`${API_BASE}/circuits/${selectedCircuitId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: { message: message.trim() } }),
          });
          if (!res.ok) {
            const text = await res.text();
            throw new Error(`Circuit execution failed: ${res.status} ${text}`);
          }
          const result = await res.json();
          if (!result.success) {
            throw new Error(`Circuit execution error: ${result.error}`);
          }
          circuitOutputs = result.variables || {};
        } catch (err: any) {
          console.error('Circuit execution failed:', err);
          set({ error: `Circuit execution failed: ${err.message}`, sending: false });
          throw new Error(`Circuit execution failed: ${err.message}`);
        }
      }
     try {
       const reply = await sendChat(message, sessionId, selectedCircuitId, circuitOutputs);
       console.log('sendMessage: got reply:', reply.slice(0, 50));
       set({ sending: false });
       return reply;
     } catch (err: any) {
       set({
         error: err.message,
         sending: false,
         messages: messages // Revert to original messages on error
       });
       throw err; // Re-throw so caller can handle it
     }
   },

  loadChat: async (sessionId: string) => {
    try {
      const { messages } = await getChat(sessionId);
      set({
        messages: messages || [],
        sessionId,
        error: null
      });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  loadSessions: async () => {
    try {
      const { sessions } = await listChats();
      set({ availableSessions: sessions || ['default'] });
    } catch (err: any) {
      // Silently handle session loading errors
      console.warn('Failed to load sessions:', err);
    }
  },

  resetChatSession: async (sessionId: string) => {
    try {
      await resetChat(sessionId);
      await get().loadChat(sessionId);
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  createNewSession: (sessionName: string) => {
    const newSessionId = sessionName.trim() || `session-${Date.now()}`;
    set({
      sessionId: newSessionId,
      messages: [],
      input: '',
      error: null
    });
  }
}));