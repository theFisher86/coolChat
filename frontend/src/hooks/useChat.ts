import { useCallback } from 'react';
import { useChatStore } from '../stores';
import { generateImageDirect, generateImageFromChat, suggestLoreFromChat } from '../api';

export const useChat = () => {
  const chatStore = useChatStore();

  const sendChatMessage = useCallback(async (message: string) => {
    await chatStore.sendMessage(message);
  }, [chatStore]);

  const switchSession = useCallback(async (sessionId: string) => {
    chatStore.setSessionId(sessionId);
    await chatStore.loadChat(sessionId);
  }, [chatStore]);

  return {
    // State
    messages: chatStore.messages,
    input: chatStore.input,
    sending: chatStore.sending,
    error: chatStore.error,
    sessionId: chatStore.sessionId,
    availableSessions: chatStore.availableSessions,

    // Actions
    sendMessage: sendChatMessage,
    setInput: chatStore.setInput,
    setError: chatStore.setError,
    setMessages: chatStore.setMessages,
    setSending: chatStore.setSending,
    switchSession,
    resetChat: chatStore.resetChatSession,
    loadSessions: chatStore.loadSessions,
    createSession: chatStore.createNewSession,
  };
};

export const useImageGeneration = () => {
  const chatStore = useChatStore();

  const generateImageFromLastMessage = useCallback(async () => {
    try {
      const result = await generateImageFromChat(chatStore.sessionId);
      chatStore.setMessages([
        ...chatStore.messages,
        { role: 'assistant', image_url: result.image_url, content: '' }
      ]);
    } catch (err: any) {
      throw new Error(err.message);
    }
  }, [chatStore]);

  const generateImage = useCallback(async (prompt: string) => {
    try {
      const result = await generateImageDirect(prompt, chatStore.sessionId);
      chatStore.setMessages([
        ...chatStore.messages,
        { role: 'assistant', image_url: result.image_url, content: prompt }
      ]);
    } catch (err: any) {
      throw new Error(err.message);
    }
  }, [chatStore]);

  return {
    generateImageFromLastMessage,
    generateImage,
  };
};

export const useLoreSuggestions = () => {
  const chatStore = useChatStore();

  const suggestLore = useCallback(async () => {
    try {
      const response = await suggestLoreFromChat(chatStore.sessionId);
      return response;
    } catch (err: any) {
      throw new Error(err.message);
    }
  }, [chatStore]);

  return {
    suggestLore,
  };
};