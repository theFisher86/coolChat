
import React, { useEffect, useState, useRef } from 'react';
import { flushSync } from 'react-dom';
import './App.css';
import * as pluginHost from './pluginHost';

// Custom hooks for Zustand stores
import { useChat, useImageGeneration, useLoreSuggestions } from './hooks/useChat';
import { useUIStore } from './stores';
import { useConfigStore } from './stores';
import { useDataStore } from './stores';

// Debug utilities
import { debugToolParsing, debugLLMResponses } from './debug';

// Message Controls Component
function MessageControls({ messageId, role, onSwipe, onEdit, onDelete, isVisible }) {
  if (!isVisible) return null;

  const handleSwipeClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Swipe clicked for message:', messageId);
    onSwipe(messageId);
  };

  const handleEditClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Edit clicked for message:', messageId);
    onEdit(messageId);
  };

  const handleDeleteClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Delete clicked for message:', messageId);
    onDelete(messageId);
  };

  return (
    <div className="message-controls">
      {role === 'assistant' && (
        <button
          className="message-btn swipe-btn"
          title="Regenerate message"
          onClick={handleSwipeClick}
        >
          🔃
        </button>
      )}
      <button
        className="message-btn edit-btn"
        title="Edit message"
        onClick={handleEditClick}
      >
        📝
      </button>
      <button
        className="message-btn delete-btn"
        title="Delete message"
        onClick={handleDeleteClick}
      >
        💀
      </button>
    </div>
  );
}

// Keep some API imports that we'll eventually move to stores too
import {
  getConfig,
  updateConfig,
  listCharacters,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  updateLoreEntry,
  createLoreEntry,
  deleteLoreEntry,
  updateLorebook,
  deleteLorebook,
  listLorebooks,
  getLorebook,
  listChats,
  resetChat,
  suggestLoreFromChat,
  getMcpServers,
  saveMcpServers,
  getMcpAwesome,
  getPrompts,
  savePrompts,
  getImageModels,
  sendChat,
  API_BASE,
} from './api.js';

// Enhanced lorebook imports
import { LorebookDashboard } from './components/lorebook/LorebookDashboard';
import { useChatStore } from './stores';
import { useLorebookStore } from './stores/lorebookStore';

// Circuit editor imports
import { CircuitEditor } from './components/circuits/CircuitEditor';

function App() {
  // Zustand store connections
  const chat = useChat();
  const uiStore = useUIStore();
  const configStore = useConfigStore();
  const chatStore = useChatStore();
  const dataStore = useDataStore();
  const lorebookStore = useLorebookStore();
  const { generateImage, generateImageFromLastMessage } = useImageGeneration();
  const { suggestLore } = useLoreSuggestions();

  const messagesRef = useRef(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editingChar, setEditingChar] = useState(null);
  const [expandedEntries, setExpandedEntries] = useState({});
  const [showSOHint, setShowSOHint] = useState(false);
  const [suppressSOHint, setSuppressSOHint] = useState(false);
  const [suggests, setSuggests] = useState([]);
  const [phoneUrl, setPhoneUrl] = useState('https://example.org');
  const [toasts, setToasts] = useState([]);
  const [menuOpen, setMenuOpen] = useState(false);

  // Message control states
  const [hoveredMessageId, setHoveredMessageId] = useState(null);
  const [controlsVisible, setControlsVisible] = useState(false);
  const hoverTimeoutRef = useRef(null);
  const swipeNavTimeoutRef = useRef(null);
  const [editingMessage, setEditingMessage] = useState(null);
  const [editText, setEditText] = useState('');
  // Message swipe states
  const [swipeHistories, setSwipeHistories] = useState({});
  const [swipeNavVisible, setSwipeNavVisible] = useState({});
  const [animatingMessage, setAnimatingMessage] = useState(null);
  const [swipeComingIn, setSwipeComingIn] = useState(null);
  const [wigglingMessage, setWigglingMessage] = useState(null);

  // Load config on mount
  useEffect(() => {
    configStore.loadConfig();
    dataStore.loadCharacters();
    dataStore.loadLorebooks();
  }, []);

  // Listen for phone style changes from AppearanceTab
  useEffect(() => {
    const h = (e) => { try { if (e && e.detail) uiStore.setPhoneStyle(e.detail); } catch {} };
    window.addEventListener('coolchat:phoneStyle', h);
    return () => window.removeEventListener('coolchat:phoneStyle', h);
  }, []);

  // Listen for theme updates (background animations, colors, etc.)
  useEffect(() => {
    const h = (e) => { try { if (e && e.detail) uiStore.updateAppTheme(e.detail); } catch {} };
    window.addEventListener('coolchat:themeUpdate', h);
    return () => window.removeEventListener('coolchat:themeUpdate', h);
  }, []);

  // Subscribe to pluginHost updates so plugin-registered animations update the theme
  useEffect(() => {
    const applyPluginAnims = () => {
      try {
        const anims = pluginHost.getBackgroundAnimations();
        uiStore.applyPluginAnimations(anims);
      } catch (e) { console.error(e); }
    };
    try { pluginHost.onUpdate(applyPluginAnims); } catch (e) {}
    applyPluginAnims();
    return () => { try { pluginHost.offUpdate(applyPluginAnims); } catch (e) {} };
  }, []);

  // Toast notification function
  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  };

  // Close menu on mobile when interacting outside or on orientation change
  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 768px)');

    const handleInteraction = (e) => {
      if (!e.target.closest('.header')) {
        setMenuOpen(false);
      }
    };

    const handleMediaChange = (e) => {
      if (!e.matches) {
        setMenuOpen(false);
      }
    };

    if (menuOpen && mediaQuery.matches) {
      document.addEventListener('click', handleInteraction);
      document.addEventListener('touchstart', handleInteraction);
      mediaQuery.addEventListener('change', handleMediaChange);
      return () => {
        document.removeEventListener('click', handleInteraction);
        document.removeEventListener('touchstart', handleInteraction);
        mediaQuery.removeEventListener('change', handleMediaChange);
      };
    }
  }, [menuOpen]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesRef.current) {
      setTimeout(() => {
        try {
          messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
        } catch (e) {
          // Silently handle scroll errors
        }
      }, 0);
    }
  }, [chat.messages]);

  // Models when provider changes and settings are open
  useEffect(() => {
    if (!uiStore.showConfig) return;
    (async () => {
      try {
        configStore.loadModels();
      } catch (e) {
        console.error('Failed to load models:', e);
      }
    })();
  }, [configStore.activeProvider, uiStore.showConfig]);

  // Load lore entries when selected lorebook changes
  useEffect(() => {
    if (dataStore.selectedLorebook) {
      dataStore.loadLoreEntries(dataStore.selectedLorebook.id);
    } else {
      dataStore.setLoreEntries([]);
    }
  }, [dataStore.selectedLorebook]);

  // Improved function to extract JSON from complex LLM responses
  const extractJsonFromResponse = (response) => {
    if (!response || typeof response !== 'string') {
      return { obj: null, captionText: '' };
    }

    let captionText = '';
    let obj = null;

    // Clean asterisks from the response
    const cleanText = response.replace(/\*+/g, '').trim();

    // Try 1: Direct JSON parse
    try {
      obj = JSON.parse(cleanText);
      return { obj, captionText: '' };
    } catch (e) {
      // Try 1 failed: Direct parse - silent
    }

    // Try 2: Extract JSON object/array from end of text using reverse brace counting
    const lastCloseIndex = Math.max(cleanText.lastIndexOf('}'), cleanText.lastIndexOf(']'));
    if (lastCloseIndex > 0) {
      const closeChar = cleanText.charAt(lastCloseIndex);
      const openChar = closeChar === '}' ? '{' : '[';
      let braceCount = 0;
      let jsonStartIndex = -1;

      for (let i = lastCloseIndex; i >= 0; i--) {
        const c = cleanText.charAt(i);
        if (c === closeChar) braceCount++;
        if (c === openChar) {
          braceCount--;
          if (braceCount === 0) {
            jsonStartIndex = i;
            break;
          }
        }
      }

      if (jsonStartIndex >= 0) {
        try {
          const jsonString = cleanText.slice(jsonStartIndex, lastCloseIndex + 1);
          obj = JSON.parse(jsonString);
          captionText = cleanText.slice(0, jsonStartIndex).trim();
          return { obj, captionText };
        } catch (e) {
          // Try 2 parse failed - silent
        }
      }
    }

    // Try 3: Look for 'toolCalls:' keyword and extract following array
    const toolCallsMatch = cleanText.match(/toolCalls\s*:?\s*(\[[\s\S]*\])$/);
    if (toolCallsMatch) {
      try {
        const arrayString = toolCallsMatch[1];
        const arrayObj = JSON.parse(arrayString);
        obj = { toolCalls: arrayObj };
        captionText = cleanText.slice(0, toolCallsMatch.index).trim();
        return { obj, captionText };
      } catch (e) {
        // Try 3 parse failed - silent
      }
    }

    // Try 4: Fallback to regex extraction (last resort)
    const fullJsonMatch = cleanText.match(/\{[\s\S]*\}/);
    if (fullJsonMatch) {
      try {
        obj = JSON.parse(fullJsonMatch[0]);
        captionText = cleanText.slice(0, fullJsonMatch.index).trim();
        return { obj, captionText };
      } catch (e) {
        // Try 4 parse failed - silent
      }
    }

    return { obj: null, captionText: '' };
  };

  // FIXED [2025-09-04]: Critical syntax error fix
  // Issue: Missing closing brace caused "Objects are not valid as a React child" error
  // Root cause: Function wasn't properly terminated, causing React to try rendering the object directly
  // Impact: Frontend showed blank screen instead of loading the application
  // Solution: Already fixed - extractJsonFromResponse function properly terminated above

  const onSubmit = async (e) => {
    e.preventDefault();
    chat.setError(null);
    const trimmed = chat.input.trim();
    if (!trimmed) return;
    try {
      console.log(`[${new Date().toISOString()}] onSubmit: Starting submit, current messages:`, chat.messages.length, 'messages');
      // Clear input first for immediate user feedback
      chat.setInput('');
      console.log(`[${new Date().toISOString()}] onSubmit: Before appending user message, messages:`, chat.messages.map(m => ({ role: m.role, content: m.content.slice(0,50) })));
      flushSync(() => chatStore.setMessages((prev) => [...prev, { role: 'user', content: trimmed } ]));
      // Use direct store access to get current messages
      const currentMessages = useChatStore.getState().messages;
      console.log(`[${new Date().toISOString()}] onSubmit: After appending user message, messages:`, currentMessages.map(m => ({ role: m.role, content: m.content.slice(0,50) })));
      const result = await chat.sendMessage(trimmed);
      await debugLLMResponses('Raw LLM response: ' + result);
      const afterSendMessages = useChatStore.getState().messages;
      console.log(`[${new Date().toISOString()}] onSubmit: after sendMessage, messages:`, afterSendMessages.map(m => ({ role: m.role, content: m.content.slice(0,50) })));
      // Try to parse tool calls using improved extraction function
      let handled = false;
      let captionText = '';
      try {
        const { obj, captionText: extractedCaptionText } = extractJsonFromResponse(result);
        captionText = extractedCaptionText;
        debugToolParsing('Extraction result: ' + JSON.stringify({ obj, captionText }));

        if (!obj) {
          debugToolParsing('No JSON extracted from response');
        }
        // Structured calls preferred: toolCalls: [{type,payload}]
        if (obj && Array.isArray(obj.toolCalls)) {
          for (const tc of obj.toolCalls) {
            if (!tc || !tc.type) continue;
            if (tc.type === 'image_request' && tc.payload?.prompt) {
              await generateImage(tc.payload.prompt);
              if (captionText) {
                flushSync(() => chatStore.setMessages((prev) => [...prev, { role: 'assistant', content: captionText }]));
              }
              handled = true;
            } else if (tc.type === 'phone_url' && tc.payload?.url) {
              let u = tc.payload.url; if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); uiStore.setPhoneOpen(true);
              if (captionText) {
                flushSync(() => chatStore.setMessages((prev) => [...prev, { role: 'assistant', content: captionText }]));
              }
              handled = true;
            } else if (tc.type === 'lore_suggestions' && Array.isArray(tc.payload?.items)) {
              console.log('[DEBUG] Lore suggestions tool call parsed (items):', tc.payload.items);
              setSuggests(tc.payload.items.map(x => ({ keyword: x.keyword, content: x.content })));
              uiStore.setSuggestOpen(true); handled = true;
            } else if (tc.type === 'lore_suggestions' && Array.isArray(tc.payload?.suggestions)) {
              console.log('[DEBUG] Lore suggestions tool call parsed (suggestions):', tc.payload.suggestions);
              setSuggests(tc.payload.suggestions.map(x => ({ keyword: x.keyword, content: x.content })));
              uiStore.setSuggestOpen(true); handled = true;
            }
          }
        } else {
          debugToolParsing('No toolCalls array found, trying flat keys');
          // Flat keys fallback
          if (obj && obj.image_request) {
            debugToolParsing('Found flat key: image_request');
            await generateImage(obj.image_request);
            handled = true;
          }
          if (obj && obj.phone_url) {
            debugToolParsing('Found flat key: phone_url');
            let u = obj.phone_url; if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); uiStore.setPhoneOpen(true);
            if (captionText) {
              debugToolParsing('Adding caption message for phone_url: ' + captionText);
              flushSync(() => chatStore.setMessages((prev) => [...prev, { role: 'assistant', content: captionText }]));
            }
            handled = true;
          }
          if (obj && Array.isArray(obj.lore_suggestions)) {
            debugToolParsing('Found flat key: lore_suggestions');
            console.log('[DEBUG] Lore suggestions flat key parsed:', obj.lore_suggestions);
            setSuggests(obj.lore_suggestions); uiStore.setSuggestOpen(true);
            handled = true;
          }

          // Check for tool call hints and structured output prompt
          const hasToolHints = /toolCalls\s*:|image_request|phone_url|lore_suggestions/i.test(result);
          if (!configStore.structuredOutput && !suppressSOHint && hasToolHints && !handled) {
            setShowSOHint(true);
          }
        }
      } catch (e) { console.warn('Tool parse failed', e); }
      debugToolParsing('Parsing complete. Handled: ' + handled + ', Caption text: ' + captionText);
      const afterProcessingMessages = useChatStore.getState().messages;
      console.log(`[${new Date().toISOString()}] onSubmit: after tool processing, handled:`, handled, 'messages:', afterProcessingMessages.map(m => ({ role: m.role, content: m.content.slice(0,50) })));

      // If no tool calls were processed, add the raw response as a regular message
      if (!handled) {
        debugToolParsing('No tool calls handled, adding response text to chat');
        flushSync(() => chatStore.setMessages((prev) => [...prev, { role: 'assistant', content: result }]));
      }
    } catch (err) {
      console.error('Error sending message:', err);
      showToast(err.message, 'error');
    }
  };

  // Message control handlers
    const handleMessageHover = (messageIndex, isEnter) => {
      if (isEnter) {
        if (hoverTimeoutRef.current) {
          clearTimeout(hoverTimeoutRef.current);
        }
        hoverTimeoutRef.current = setTimeout(() => {
          setHoveredMessageId(messageIndex);
          setControlsVisible(true);
        }, 300);
      } else {
        if (hoverTimeoutRef.current) {
          clearTimeout(hoverTimeoutRef.current);
        }
        setControlsVisible(false);
        setHoveredMessageId(null);
      }
    };

    const handleSwipeNavHover = (messageIndex, isEnter) => {
      if (isEnter) {
        if (swipeNavTimeoutRef.current) {
          clearTimeout(swipeNavTimeoutRef.current);
        }
        swipeNavTimeoutRef.current = setTimeout(() => {
          setSwipeNavVisible(prev => ({ ...prev, [messageIndex]: true }));
        }, 300);
      } else {
        if (swipeNavTimeoutRef.current) {
          clearTimeout(swipeNavTimeoutRef.current);
        }
        setSwipeNavVisible(prev => ({ ...prev, [messageIndex]: false }));
      }
    };

    // Hide controls when tapping outside a message
    useEffect(() => {
      const handleTouchOutside = (e) => {
        if (!e.target.closest('.message')) {
          setControlsVisible(false);
          setHoveredMessageId(null);
        }
      };
      document.addEventListener('touchstart', handleTouchOutside);
      return () => document.removeEventListener('touchstart', handleTouchOutside);
    }, []);

    const handleSwipe = async (messageIndex) => {
      setControlsVisible(false);
      try {
        let messages = chat.messages;

        if (messageIndex >= messages.length || messageIndex < 0) {
          showToast('Message not found', 'error');
          return;
        }

        const message = messages[messageIndex];
        if (message.role !== 'assistant') {
          showToast('Only assistant messages can be regenerated', 'error');
          return;
        }

        // Find the user message that precedes this assistant message
        let userMessageContent = null;
        for (let i = messageIndex - 1; i >= 0; i--) {
          if (messages[i].role === 'user') {
            userMessageContent = messages[i].content;
            break;
          }
        }

        if (!userMessageContent) {
          showToast('No user message found to regenerate from', 'error');
          return;
        }

        // Trigger swipe animation - message pushes out to the left
        setAnimatingMessage(messageIndex);

        // Small delay to show animation before API call
        setTimeout(async () => {
          chat.setSending(true);
          chat.setError(null);

          // Initialize swipe history for this message if it doesn't exist
          if (!swipeHistories[messageIndex]) {
            swipeHistories[messageIndex] = {
              currentIndex: 0,
              generations: [message.content]
            };
          }

          try {
            // Send just the user message content to generate a new response (not as part of conversation)
            const reply = await sendChat(userMessageContent, chat.sessionId);
            await debugLLMResponses('Raw LLM response after swipe: ' + reply);

            // Add the new generation to history
            const swipeHistory = swipeHistories[messageIndex];
            swipeHistory.generations.push(reply);
            swipeHistory.currentIndex = swipeHistory.generations.length - 1; // Go to latest

            // Update message content to the new generation
            const updatedMessages = [...messages];
            updatedMessages[messageIndex] = {
              ...message,
              content: reply
            };

            chat.setMessages(updatedMessages);
            setSwipeHistories({ ...swipeHistories });

            // Clear the outgoing animation and start incoming animation
            setAnimatingMessage(null);
            setSwipeComingIn(messageIndex); // Start incoming animation

            // Clear incoming animation after it completes
            setTimeout(() => {
              setSwipeComingIn(null);
            }, 800); // Match CSS animation duration

            chat.setSending(false);
            showToast('Message regenerated successfully', 'success');
          } catch (err) {
            console.error('Error during swipe:', err);
            chat.setSending(false);
            setAnimatingMessage(null); // Stop animation on error
            setSwipeComingIn(null); // Clear any incoming animation
            showToast('Failed to regenerate message: ' + err.message, 'error');
          }
        }, 300); // Delay to show swipe-out animation

      } catch (err) {
        console.error('Error during swipe:', err);
        showToast('Failed to regenerate message: ' + err.message, 'error');
        setAnimatingMessage(null);
      }
    };

    const handleEdit = (messageIndex) => {
      setControlsVisible(false);
      const message = chat.messages[messageIndex];
      if (message) {
        setEditingMessage(messageIndex);
        setEditText(message.content);
      }
    };

    const handleSaveEdit = async () => {
      if (!editingMessage || !editText.trim()) return;

      try {
        const messageIndex = editingMessage;

        // Create updated messages array
        const updatedMessages = [...chat.messages];
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          content: editText.trim()
        };

        chat.setMessages(updatedMessages);
        setEditingMessage(null);
        setEditText('');

        showToast('Message edited successfully', 'success');

      } catch (err) {
        console.error('Error editing message:', err);
        showToast('Failed to edit message: ' + err.message, 'error');
      }
    };

    const handleCancelEdit = () => {
      setEditingMessage(null);
      setEditText('');
    };

    const handleDelete = (messageIndex) => {
      setControlsVisible(false);

      if (messageIndex >= chat.messages.length || messageIndex < 0) return;

      // Clean up swipe history for this message
      const newSwipeHistories = { ...swipeHistories };
      delete newSwipeHistories[messageIndex];

      // Adjust indices for messages after the deleted one
      const adjustedSwipeHistories = {};
      Object.entries(newSwipeHistories).forEach(([idx, history]) => {
        const numIdx = parseInt(idx);
        if (numIdx > messageIndex) {
          adjustedSwipeHistories[numIdx - 1] = history;
        } else {
          adjustedSwipeHistories[numIdx] = history;
        }
      });

      // Create updated messages array without the deleted message
      const updatedMessages = chat.messages.filter((_, idx) => idx !== messageIndex);
      chat.setMessages(updatedMessages);
      setSwipeHistories(adjustedSwipeHistories);

      showToast('Message deleted', 'success');
    };

    const handleSwipePrevious = (messageIndex) => {
      const swipeHistory = swipeHistories[messageIndex];
      if (!swipeHistory || swipeHistory.currentIndex > 0) {
        const newIndex = Math.max(0, (swipeHistory?.currentIndex ?? 0) - 1);

        // Update message content
        const updatedMessages = [...chat.messages];
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          content: swipeHistory.generations[newIndex]
        };

        // Update current index
        const updatedSwipeHistories = { ...swipeHistories };
        updatedSwipeHistories[messageIndex] = {
          ...swipeHistory,
          currentIndex: newIndex
        };

        chat.setMessages(updatedMessages);
        setSwipeHistories(updatedSwipeHistories);

        // Trigger horizontal flip animation
        setWigglingMessage(messageIndex);
        setTimeout(() => {
          setWigglingMessage(null);
        }, 1000); // Match animation duration
      }
    };

    const handleSwipeNext = (messageIndex) => {
      const swipeHistory = swipeHistories[messageIndex];
      if (!swipeHistory || swipeHistory.currentIndex < swipeHistory.generations.length - 1) {
        const newIndex = Math.min(
          (swipeHistory?.generations.length ?? 1) - 1,
          (swipeHistory?.currentIndex ?? 0) + 1
        );

        // Update message content
        const updatedMessages = [...chat.messages];
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          content: swipeHistory.generations[newIndex]
        };

        // Update current index
        const updatedSwipeHistories = { ...swipeHistories };
        updatedSwipeHistories[messageIndex] = {
          ...swipeHistory,
          currentIndex: newIndex
        };

        chat.setMessages(updatedMessages);
        setSwipeHistories(updatedSwipeHistories);

        // Trigger horizontal flip animation
        setWigglingMessage(messageIndex);
        setTimeout(() => {
          setWigglingMessage(null);
        }, 1000); // Match animation duration
      }
    };

  return (
    <div className={`app ${uiStore.phoneOpen ? 'phone-open' : ''}`}>
     <div className="bg-animations">
       {(uiStore.appTheme?.background_animations||[]).map((id, idx) => (
         <div key={idx} className={`anim-${id}`} />
       ))}
     </div>
     <header className={`header ${menuOpen ? 'menu-open' : ''}`} role="banner">
       <h1>CoolChat</h1>
       <div className="spacer" />
       <div className="header-buttons">
         <button className="secondary" aria-label={uiStore.showCharacters ? 'Hide characters panel' : 'Show characters panel'} aria-expanded={uiStore.showCharacters} onClick={() => uiStore.setShowCharacters(!uiStore.showCharacters)}>
           {uiStore.showCharacters ? 'Hide Characters' : 'Characters'}
         </button>
         <button className="secondary" aria-label={uiStore.showChats ? 'Hide chats panel' : 'Show chats panel'} aria-expanded={uiStore.showChats} onClick={() => uiStore.setShowChats(!uiStore.showChats)}>
           {uiStore.showChats ? 'Hide Chats' : 'Chats'}
         </button>
         <button className="secondary" aria-label={uiStore.showTools ? 'Hide tools panel' : 'Show tools panel'} aria-expanded={uiStore.showTools} onClick={() => uiStore.setShowTools(!uiStore.showTools)}>
           {uiStore.showTools ? 'Hide Tools' : 'Tools'}
         </button>
         <button className="secondary" aria-label={uiStore.showLorebooks ? 'Hide lorebooks panel' : 'Show lorebooks panel'} aria-expanded={uiStore.showLorebooks} onClick={() => uiStore.setShowLorebooks(!uiStore.showLorebooks)}>
           {uiStore.showLorebooks ? 'Hide Lorebooks' : 'Lorebooks'}
         </button>
         <button className="secondary" aria-label={uiStore.showCircuits ? 'Hide circuits panel' : 'Show circuits panel'} aria-expanded={uiStore.showCircuits} onClick={() => uiStore.setShowCircuits(!uiStore.showCircuits)}>
           {uiStore.showCircuits ? 'Hide Circuits' : 'Circuits'}
         </button>
         <button className="secondary" aria-label={uiStore.phoneOpen ? 'Close phone simulator' : 'Open phone simulator'} aria-expanded={uiStore.phoneOpen} onClick={() => uiStore.setPhoneOpen(!uiStore.phoneOpen)}>
           {uiStore.phoneOpen ? 'Close Phone' : 'Phone'}
         </button>
     <button className="secondary" aria-label={uiStore.showConfig ? 'Close settings' : 'Open settings'} aria-expanded={uiStore.showConfig} onClick={() => uiStore.setShowConfig(!uiStore.showConfig)}>
       {uiStore.showConfig ? 'Close Settings' : 'Settings'}
     </button>
       </div>
       <button className="menu-toggle" aria-label="Toggle menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
         ☰
       </button>
     </header>

      {uiStore.phoneOpen && (
        <div className={`phone-panel ${uiStore.phoneStyle}`}>
          <div className="outer-overlay" onClick={(e) => { if (e.target === e.currentTarget) uiStore.setPhoneOpen(false); }}></div>
          <div className="skin"></div>
          <div className="screen">
            <div className="statusbar">
              {uiStore.phoneStyle === 'iphone' ? (
                <>
                  <span className="left">📶</span>
                  <span className="time">{new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                  <span className="right">🔊 📶</span>
                </>
              ) : (
                <>
                  <span>{new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                  <span>📶 📍 🔔</span>
                </>
              )}
            </div>
            <div className="bar">
              <input style={{ flex: 1 }} placeholder="https://" value={phoneUrl} onChange={(e)=> setPhoneUrl(e.target.value)} />
              <button className="secondary" onClick={()=> { let u = phoneUrl; if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); }}>Go</button>
              <button className="secondary" title="Open in new tab" onClick={()=> { try { let u = phoneUrl; if (!/^https?:/i.test(u)) u = 'https://' + u; window.open(u, '_blank'); } catch (e) { console.error(e);} }}>✨</button>
            </div>
            <iframe src={/^https?:/i.test(phoneUrl) ? phoneUrl : ('https://' + phoneUrl)} title="Phone" onLoad={()=>{ try { fetch(`${API_BASE}/phone/debug`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ event:'load', url: phoneUrl }) }); } catch (e) { console.error(e);} }} onError={()=>{ try { fetch(`${API_BASE}/phone/debug`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ event:'error', url: phoneUrl }) }); } catch (e) { console.error(e);} }} />
          </div>
        </div>
      )}
      <main className="chat">

        {uiStore.showCharacters && (
          <section className="characters overlay">
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0 }}>Characters</h2>
              <button className="secondary" onClick={() => uiStore.setShowCharacters(false)}>Close</button>
            </div>
            <div className="row">
              <label className="secondary" style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>
                Import JSON/PNG
                <input type="file" accept="application/json,.json,image/png" style={{ display: 'none' }} onChange={async (e) => {
                  const f = e.target.files?.[0]; if (!f) return;
                  try {
                    if (f.type === 'image/png') {
                      const fd = new FormData(); fd.append('file', f);
                      const res = await fetch(`${API_BASE}/characters/import`, { method: 'POST', body: fd });
                      if (!res.ok) throw new Error('Import failed');
                    } else {
                      const text = await f.text(); const data = JSON.parse(text); if (!data.name) throw new Error('JSON must include name'); await createCharacter({ name: data.name, description: data.description || '', avatar_url: data.avatar_url || null });
                    }
                    dataStore.loadCharacters();
                  } catch (err) { alert(err.message); }
                  e.target.value = '';
                }} />
              </label>
              <button className="secondary" onClick={() => dataStore.loadCharacters()}>Refresh</button>
            </div>

            <div className="char-grid">
              <div className="char-card" onClick={() => { setEditingChar(null); setEditorOpen(true); }}>
                <img src={'https://placehold.co/400x600?text=New+Character'} alt="New Character" />
                <div className="name">+ New</div>
              </div>
              {dataStore.characters.map(c => (
                <div key={c.id} className="char-card">
                  <img src={c.avatar_url || 'https://placehold.co/400x600?text=Character'} alt={c.name} />
                  <div className="name">{c.name}</div>
                  <div className="cog" onClick={(e) => { e.stopPropagation(); setEditingChar(c); setEditorOpen(true); }}><span>⚙️</span></div>
                  <div style={{ padding: '8px' }}>
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                    <button onClick={async () => { try { await updateConfig({ active_character_id: c.id }); uiStore.setShowCharacters(false);} catch (e) { console.error(e); alert(e.message); } }}>Use</button>
                      <button className="secondary" onClick={async () => { try { await deleteCharacter(c.id); dataStore.loadCharacters();} catch (e) { alert(e.message);} }}>Delete</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {uiStore.showChats && (
          <section className="panel overlay">
            <h2>Chats</h2>
            <ChatManager sessionId={chat.sessionId} setSessionId={chat.switchSession} onClose={() => uiStore.setShowChats(false)} />
          </section>
        )}

        {uiStore.showTools && (
          <section className="panel overlay">
            <h2>Tools</h2>
            <ToolsOverlay onClose={() => uiStore.setShowTools(false)} />
          </section>
        )}

        {uiStore.showConfig && (
          <section className="panel overlay">
            <h2>Configuration</h2>
            <div className="row" style={{ gap: 6, marginBottom: 8 }}>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('connection'); }}>Connection</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('persona'); }}>Persona</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('appearance'); }}>Appearance</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('images'); }}>Images</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('prompts'); }}>Prompts</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('advanced'); }}>Advanced</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); uiStore.setSettingsTab('extensions'); }}>Extensions</button>
            </div>
            {uiStore.settingsTab === 'connection' && (
              <form
                className="config-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    const cfg = await getConfig();
                    const current = configStore.providers?.[configStore.activeProvider] || {};
                    const changes = {};
                    for (const k of ['api_key','api_base','model','temperature']) {
                      const nv = configStore.configDraft[k];
                      const ov = current[k] ?? '';
                      if (k === 'temperature') { if (typeof nv === 'number' && nv !== ov) changes[k] = nv; }
                      else if (nv && nv !== ov) { changes[k] = nv; }
                    }
                    if (Object.keys(changes).length) {
                      const lines = Object.entries(changes).map(([k,v])=>`- ${k}: old=${current[k] ?? '(none)'} -> new=${v}`).join('\n');
                      if (!window.confirm(`Config.json already has this information, would you like to update it or discard?\n${lines}`)) {
                        configStore.setConfigDraft({ api_key: '', api_base: current.api_base || '', model: current.model || '', temperature: current.temperature ?? 0.7 });
                        return;
                      }
                    }
                    const updated = await updateConfig({ active_provider: configStore.activeProvider, providers: { [configStore.activeProvider]: changes }, max_context_tokens: configStore.maxTokens });
                    configStore.setProviders(updated.providers || {});
                  } catch (e) { console.error(e); alert(e.message); }
                }}
              >
                <label>
                  <span>Provider</span>
                  <select
                    value={configStore.activeProvider}
                    onChange={async (e) => {
                      const next = e.target.value;
                      configStore.setActiveProvider(next);
                      const cur = configStore.providers[next] || {};
                      configStore.setConfigDraft({ api_key: '', api_base: cur.api_base || '', model: cur.model || '', temperature: cur.temperature ?? 0.7 });
                      try { await configStore.updateProvider(next); } catch {}
                    }}
                  >
                    <option value="echo">Echo (no API key)</option>
                    <option value="openai">OpenAI-compatible</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="gemini">Google Gemini</option>
                  </select>
                </label>

                <label>
                  <span>API Key</span>
                  <input
                    type="password"
                    placeholder={configStore.providers[configStore.activeProvider]?.api_key_masked ? `Saved: ${configStore.providers[configStore.activeProvider].api_key_masked}` : 'sk-...'}
                    value={configStore.configDraft.api_key}
                    onChange={(e) => configStore.setConfigDraft({ ...configStore.configDraft, api_key: e.target.value })}
                  />
                </label>

                <label>
                  <span>API Base</span>
                  <input
                    type="text"
                    placeholder={
                      configStore.activeProvider === 'openrouter'
                        ? 'https://openrouter.ai/api/v1'
                        : configStore.activeProvider === 'openai'
                        ? 'https://api.openai.com/v1'
                        : 'https://generativelanguage.googleapis.com/v1beta/openai'
                    }
                    value={configStore.configDraft.api_base}
                    onChange={(e) => configStore.setConfigDraft({ ...configStore.configDraft, api_base: e.target.value })}
                  />
                </label>

                <label>
                  <span>Model</span>
                  {configStore.modelList.length > 0 ? (
                    <select
                      value={configStore.configDraft.model || ''}
                      onChange={(e) => configStore.setConfigDraft({ ...configStore.configDraft, model: e.target.value })}
                      >
                      <option value="">{configStore.loadingModels ? 'Loading…' : 'Select a model'}</option>
                      {configStore.modelList.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      placeholder={configStore.activeProvider === 'gemini' ? 'gemini-1.5-flash' : 'gpt-4o-mini'}
                      value={configStore.configDraft.model}
                      onChange={(e) => configStore.setConfigDraft({ ...configStore.configDraft, model: e.target.value })}
                    />
                  )}
                </label>

                <div className="row">
                  <button type="button" className="secondary" onClick={async () => {
                    try {
                      await configStore.updateProviderConfig(configStore.activeProvider, configStore.configDraft);
                    } catch {
                      console.warn('Failed to update provider config');
                    }
                    try {
                      await configStore.loadModelsForProvider(configStore.activeProvider);
                    } catch {
                      configStore.setModelList([]);
                    }
                  }} disabled={configStore.loadingModels}>
                    {configStore.loadingModels ? 'Refreshing…' : 'Refresh models'}
                  </button>
                </div>

                <label>
                  <span>Temperature</span>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={configStore.configDraft.temperature}
                    onChange={(e) => configStore.setConfigDraft({ ...configStore.configDraft, temperature: parseFloat(e.target.value) })}
                  />
                </label>
                <label>
                  <span>Structured Output (Gemini)</span>
                  <input type="checkbox" checked={configStore.structuredOutput} onChange={async (e)=> { try { await configStore.updateStructuredOutput(e.target.checked); } catch (err) { alert(err.message); } }} />
                </label>

                <div className="row">
                  <button type="submit">Save</button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => configStore.setConfigDraft({
                      api_key: '',
                      api_base: configStore.providers[configStore.activeProvider]?.api_base || '',
                      model: configStore.providers[configStore.activeProvider]?.model || '',
                      temperature: configStore.providers[configStore.activeProvider]?.temperature ?? 0.7,
                    })}
                  >
                    Reset
                  </button>
                </div>
                <label>
                  <span>Max Context Tokens ({configStore.maxTokens})</span>
                  <input type="range" min="512" max="8192" step="128" value={configStore.maxTokens} onChange={(e)=> configStore.updateMaxTokens(parseInt(e.target.value,10))} />
                </label>
              </form>
            )}
            {uiStore.settingsTab === 'persona' && (
              <div className="config-form">
                <label>
                  <span>User Name</span>
                  <input value={configStore.userPersona.name} onChange={(e) => configStore.setUserPersona({ ...configStore.userPersona, name: e.target.value })} onBlur={async () => { try { await configStore.updateUserPersona(configStore.userPersona); } catch (e) { console.error(e); alert(e.message);} }} />
                </label>
                <label>
                  <span>User Description</span>
                  <textarea rows={3} value={configStore.userPersona.description} onChange={(e) => configStore.setUserPersona({ ...configStore.userPersona, description: e.target.value })} onBlur={async () => { try { await configStore.updateUserPersona(configStore.userPersona); } catch (e) { console.error(e); alert(e.message);} }} />
                </label>
              </div>
            )}

            {uiStore.settingsTab === 'debug' && (
              <div className="config-form">
                <label>
                  <span>Log Prompts</span>
                  <input type="checkbox" checked={configStore.debugFlags.log_prompts} onChange={async (e) => { const v = e.target.checked; const updated = { ...configStore.debugFlags, log_prompts: v }; configStore.setDebug
