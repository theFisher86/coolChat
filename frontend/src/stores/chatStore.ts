import { create } from 'zustand';
import { sendChat, getChat, listChats, resetChat } from '../api';

export interface ChatState {
  // Chat content state
  messages: any[];
  input: string;
  sending: boolean;
  error: string | null;

  // Session management
  sessionId: string;
  availableSessions: string[];

  // Actions
  setMessages: (messages: any[]) => void;
  setInput: (input: string) => void;
  setSending: (sending: boolean) => void;
  setError: (error: string | null) => void;
  setSessionId: (sessionId: string) => void;
  setAvailableSessions: (sessions: string[]) => void;

  // Async actions
  sendMessage: (message: string) => Promise<void>;
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

  // Basic setters
  setMessages: (messages) => set({ messages }),
  setInput: (input) => set({ input }),
  setSending: (sending) => set({ sending }),
  setError: (error) => set({ error }),
  setSessionId: (sessionId) => set({ sessionId }),
  setAvailableSessions: (availableSessions) => set({ availableSessions }),

  // Async actions
  sendMessage: async (message: string) => {
    if (!message.trim() || get().sending) return;

    const { sessionId, messages } = get();
    const userMsg = { role: 'user', content: message.trim() };

    set({
      sending: true,
      input: '',
      error: null,
      messages: [...messages, userMsg]
    });

    try {
      const reply = await sendChat(message, sessionId);
      set((state) => ({
        messages: [...state.messages, { role: 'assistant', content: reply }],
        sending: false
      }));
    } catch (err: any) {
      set({
        error: err.message,
        sending: false
      });
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