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

  // Close menu on mobile when clicking outside or on a button
  useEffect(() => {
    const handleClick = (e) => {
      if (window.innerWidth <= 768 && !e.target.closest('.header')) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
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
  }

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
      console.log(`[${new Date().toISOString()}] onSubmit: after sendMessage, current messages:`, afterSendMessages.map(m => ({ role: m.role, content: m.content.slice(0,50) })));
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

  // Load extensions state on mount
  const [extensions, setExtensions] = useState([]);
  const [extensionsEnabled, setExtensionsEnabled] = useState({});
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/plugins`);
        if (r.ok) {
          const data = await r.json();
          // Plugins loaded successfully
          setExtensions(data.plugins || []);
          setExtensionsEnabled(data.enabled || {});
          // Let pluginHost know about enabled map
          try { pluginHost.setEnabledExtensions(data.enabled || {}); } catch (e) {}
          // Attempt to load enabled plugins
          try { await pluginHost.loadPlugins(); } catch (e) { console.error(e); }
        }
      } catch (e) { console.error('Failed to load plugins', e); }
    })();
  }, []);

  const saveExtensionsEnabled = async (map) => {
    try {
      const r = await fetch(`${API_BASE}/plugins/enabled`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(map) });
      if (!r.ok) throw new Error('Save failed');
      setExtensionsEnabled(map);
      try {
        pluginHost.setEnabledExtensions(map);
        // Give pluginHost the already-fetched manifest so it can reload deterministically
        const manifestResp = await fetch(`${API_BASE}/plugins`);
        const manifestData = manifestResp.ok ? await manifestResp.json() : null;
        if (manifestData) pluginHost.setExtensionsList(manifestData.plugins || []);
        await pluginHost.loadPlugins(manifestData);
      } catch (e) { console.error(e); }
      // Also persist to the main settings.json via updateConfig
      try { await updateConfig({ extensions: map }); } catch (e) { console.error('Failed to persist extensions to config', e); }
    } catch (e) { console.error(e); alert(e.message); }
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
                  <input type="checkbox" checked={configStore.debugFlags.log_prompts} onChange={async (e) => { const v = e.target.checked; const updated = { ...configStore.debugFlags, log_prompts: v }; configStore.setDebugFlags(updated); try { await configStore.updateDebugFlags(updated); } catch {} }} />
                </label>
                <label>
                  <span>Log Responses</span>
                  <input type="checkbox" checked={configStore.debugFlags.log_responses} onChange={async (e) => { const v = e.target.checked; const updated = { ...configStore.debugFlags, log_responses: v }; configStore.setDebugFlags(updated); try { await configStore.updateDebugFlags(updated); } catch {} }} />
                </label>
                <label>
                  <span>Max Context Tokens ({configStore.maxTokens})</span>
                  <input type="range" min="512" max="8192" step="128" value={configStore.maxTokens} onChange={async (e) => { const v = parseInt(e.target.value,10); configStore.updateMaxTokens(v); try { await updateConfig({ max_context_tokens: v }); } catch {} }} />
                </label>
                <label>
                  <span>User Name</span>
                  <input value={configStore.userPersona.name} onChange={(e) => configStore.setUserPersona({ ...configStore.userPersona, name: e.target.value })} onBlur={async () => { try { await configStore.updateUserPersona(configStore.userPersona); } catch {} }} />
                </label>
                <label>
                  <span>User Description</span>
                  <textarea rows={3} value={configStore.userPersona.description} onChange={(e) => configStore.setUserPersona({ ...configStore.userPersona, description: e.target.value })} onBlur={async () => { try { await configStore.updateUserPersona(configStore.userPersona); } catch {} }} />
                </label>
              </div>
            )}
            {uiStore.settingsTab === 'appearance' && (
              <AppearanceTab />
            )}
            {uiStore.settingsTab === 'images' && (
              <ImagesTab providers={configStore.providers} />
            )}
            {uiStore.settingsTab === 'prompts' && (
              <PromptsTab />
            )}
            {uiStore.settingsTab === 'advanced' && (
              <AdvancedTab />
            )}
            {uiStore.settingsTab === 'extensions' && (
              <div className="config-form">
                <h3>Extensions</h3>
                <p className="muted">Detected extensions found under /extensions. Enable ones you trust.</p>
                <div style={{ marginTop: 8 }}>
                    {extensions.length === 0 ? (
                      <div className="muted">No extensions detected. If you expect extensions, verify the backend is running and that <code>/plugins</code> returns manifests.</div>
                    ) : null}
                    {extensions.map((ext) => (
                    <div key={ext.id} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
                      <div style={{ flex: 1 }}>
                        <strong>{ext.name || ext.id}</strong>
                        <div className="muted">{ext.description || ''}</div>
                      </div>
                      <label><input type="checkbox" checked={!!extensionsEnabled[ext.id]} onChange={(e) => {
                        const next = { ...extensionsEnabled, [ext.id]: e.target.checked };
                        saveExtensionsEnabled(next);
                      }} /> Enabled</label>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {uiStore.settingsTab === 'connection' && (
              <div className="hint">
                <p className="muted">
                  OpenRouter uses OpenAI-compatible endpoints. You can set API Base to https://openrouter.ai/api/v1. Gemini uses the OpenAI-compatible base at https://generativelanguage.googleapis.com/v1beta/openai.
                </p>
              </div>
            )}
          </section>
        )}

        {uiStore.showLorebooks && (
          <section className="panel overlay">
            <LorebookDashboard onClose={() => uiStore.setShowLorebooks(false)} />
          </section>
        )}

        <div className="messages" aria-live="polite" ref={messagesRef}>
            {(() => {
              const renderMessages = useChatStore.getState().messages;
              console.log(`[${new Date().toISOString()}] Messages render: ${renderMessages.length} messages`, renderMessages.map(m => ({ role: m.role, content: m.content.slice(0,50) })));
              return null;
            })()}
            {chatStore.messages.map((m, idx) => {
              const messageId = m.id || `msg-${idx}`;
              const isHovered = hoveredMessageId === idx && controlsVisible;
              const isEditingThis = editingMessage === idx;
              const isAnimating = animatingMessage === idx;
              const isIncoming = swipeComingIn === idx;
              const isWiggling = wigglingMessage === idx;
              const hasSwipeHistory = swipeHistories[idx] && swipeHistories[idx].generations.length > 1;
              const swipeNavHovered = swipeNavVisible[idx] || false;

              return (
                <div
                  key={messageId}
                  className={`message ${m.role}${isHovered ? ' message-hovered' : ''}${isEditingThis ? ' message-editing' : ''}${isAnimating ? ' message-animating-swipe' : ''}${isIncoming ? ' message-swipe-new' : ''}${isWiggling ? ' message-flip' : ''}`}
                  onMouseEnter={() => {
                    handleMessageHover(idx, true);
                    if (hasSwipeHistory) handleSwipeNavHover(idx, true);
                  }}
                  onMouseLeave={() => {
                    handleMessageHover(idx, false);
                    if (hasSwipeHistory) handleSwipeNavHover(idx, false);
                  }}
                  onTouchStart={() => {
                    handleMessageHover(idx, true);
                    if (hasSwipeHistory) handleSwipeNavHover(idx, true);
                  }}
                  onTouchEnd={() => {
                    handleMessageHover(idx, false);
                    if (hasSwipeHistory) handleSwipeNavHover(idx, false);
                  }}
                >
                  <div className={`bubble ${hasSwipeHistory ? 'has-swipes' : ''}`}>
                    <div className="bubble-content">
                      {m.image_url ? (
                        <div>
                          <img src={m.image_url} alt="generated" style={{ maxWidth: '100%', borderRadius: 8 }} />
                          {m.content ? (<div className="img-caption">{m.content}</div>) : null}
                        </div>
                      ) : (
                        <>
                          {isEditingThis ? (
                            <div className="message-edit-container">
                              <textarea
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                className="message-edit-input"
                                autoFocus
                                rows={Math.ceil(editText.length / 60)}
                              />
                              <div className="message-edit-buttons">
                                <button className="message-edit-save" onClick={handleSaveEdit}>💾 Save</button>
                                <button className="message-edit-cancel" onClick={handleCancelEdit}>❌ Cancel</button>
                              </div>
                            </div>
                          ) : (
                            m.content
                          )}
                        </>
                      )}
                    </div>
                    {m.role === 'assistant' && hasSwipeHistory && swipeNavHovered && (
                      <div className="swipe-navigation">
                        <button
                          className="swipe-nav-btn swipe-nav-prev"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleSwipePrevious(idx);
                          }}
                          disabled={swipeHistories[idx].currentIndex === 0}
                          title="Previous generation"
                        >
                          ⬅️
                        </button>
                        <span className="swipe-count">
                          {`${swipeHistories[idx].currentIndex + 1}/${swipeHistories[idx].generations.length}`}
                        </span>
                        <button
                          className="swipe-nav-btn swipe-nav-next"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleSwipeNext(idx);
                          }}
                          disabled={swipeHistories[idx].currentIndex === swipeHistories[idx].generations.length - 1}
                          title="Next generation"
                        >
                          ➡️
                        </button>
                      </div>
                    )}
                    {m.role === 'assistant' && (
                      <div className="swipe-navigation">
                        {swipeHistories[idx] && swipeHistories[idx].generations.length > 1 && (
                          <>
                            <button
                              className="swipe-nav-btn swipe-nav-prev"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                handleSwipePrevious(idx);
                              }}
                              disabled={swipeHistories[idx].currentIndex === 0}
                              title="Previous generation"
                            >
                              ⬅️
                            </button>
                            <span className="swipe-count">
                              {swipeHistories[idx].generations.length > 1 &&
                                `${swipeHistories[idx].currentIndex + 1}/${swipeHistories[idx].generations.length}`
                              }
                            </span>
                            <button
                              className="swipe-nav-btn swipe-nav-next"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                handleSwipeNext(idx);
                              }}
                              disabled={swipeHistories[idx].currentIndex === swipeHistories[idx].generations.length - 1}
                              title="Next generation"
                            >
                              ➡️
                            </button>
                          </>
                        )}
                      </div>
                    )}
                    <MessageControls
                      messageId={idx}
                      role={m.role}
                      onSwipe={handleSwipe}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                      isVisible={isHovered}
                    />
                  </div>
                </div>
              );
            })}
           {chat.error && (
             <div className="message error">
               <div className="bubble">{chat.error}</div>
             </div>
           )}
         </div>

        <div className="input-tools">
    <button className="secondary" aria-label="Suggest lore entries from chat" title="Suggest lore entries from chat" onClick={async () => {
      try {
        const result = await suggestLore(chat.sessionId);
        if (!result.suggestions || result.suggestions.length === 0) { alert('No suggestions'); return; }
        setSuggests(result.suggestions);
        uiStore.setSuggestOpen(true);
      } catch (e) { console.error(e); alert(e.message); }
    }}>📖</button>
    <button className="secondary" aria-label="Generate image from chat" title="Generate image from chat" onClick={generateImageFromLastMessage}>🎨</button>
            <button className="secondary" aria-label="Send URL to phone simulator" title="Send URL to phone" onClick={() => { let u = prompt('Open URL on phone:'); if (u) { if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); uiStore.setPhoneOpen(true); } }}>📱</button>
           <button className="secondary" aria-label="Scroll to bottom of messages" title="Scroll to bottom" style={{ marginLeft: 'auto' }} onClick={() => {
             try {
               // Find all assistant message elements
               const assistantMessages = document.querySelectorAll('.message.assistant');

               if (assistantMessages.length > 0) {
                 // Get the last assistant message and scroll to it
                 const lastMessage = assistantMessages[assistantMessages.length - 1];
                 lastMessage.scrollIntoView({
                   behavior: 'smooth',
                   block: 'end',
                   inline: 'nearest'
                 });
               } else {
                 // Fallback to scrolling the messages container to bottom
                 if (messagesRef.current) {
                   messagesRef.current.scrollTo({
                     top: messagesRef.current.scrollHeight,
                     behavior: 'smooth'
                   });
                 }
               }
             } catch (error) {
               console.error('Error scrolling to last message:', error);
             }
           }}>⬇️</button>
        </div>
        <form className="input-row" onSubmit={onSubmit}>
           <input
             type="text"
             placeholder="Type your message"
             value={chat.input}
             onChange={(e) => chat.setInput(e.target.value)}
             onKeyDown={(e) => { if (e.ctrlKey && e.key === 'Enter') onSubmit(e); }}
             disabled={chat.sending}
             aria-label="Message input (Ctrl+Enter to send)"
             aria-describedby="send-button"
           />
           <button type="submit" id="send-button" disabled={chat.sending || !chat.input.trim()}>
             {chat.sending ? (
               <span className="loading-text">
                 <div className="spinner"></div>
                 Sending…
               </span>
             ) : 'Send'}
           </button>
         </form>

        {editorOpen && (
          <CharacterEditor
            character={editingChar}
            lorebooks={dataStore.lorebooks}
            onClose={() => setEditorOpen(false)}
            onSave={async (draft) => {
              try {
                if (editingChar) {
                  await updateCharacter(editingChar.id, draft);
                } else {
                  debugToolParsing('No toolCalls array found, trying flat keys');
                  await createCharacter(draft);
                }
                dataStore.loadCharacters();
                setEditorOpen(false);
              } catch (e) { alert(e.message); }
            }}
            onThink={async (field, draft) => {
              try {
                const payload = { ...draft };
                if (typeof payload.alternate_greetings === 'string') {
                  payload.alternate_greetings = payload.alternate_greetings.split(',').map(s => s.trim()).filter(Boolean);
                }
                if (typeof payload.tags === 'string') {
                  payload.tags = payload.tags.split(',').map(s => s.trim()).filter(Boolean);
                }
                const res = await suggestCharacterField(field, payload);
                return res.value;
              } catch (e) { alert(e.message); return ''; }
            }}
          />
        )}
        {uiStore.suggestOpen && (
           <SuggestLoreModal suggestions={suggests} onClose={() => uiStore.setSuggestOpen(false)} onApply={async (edited, targetLbId) => {
            try {
              const cfg = await getConfig();
              const activeIds = cfg.active_lorebook_ids || [];
              const lbId = targetLbId || activeIds[0];
              if (!lbId) { alert('No active lorebooks set'); return; }
              const newIds = [];
              for (const sug of edited.filter(x=>x.include)) {
                const r = await fetch(`${API_BASE}/lore`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keyword: sug.keyword, content: sug.content })});
                if (r.ok) { const e = await r.json(); newIds.push(e.id); }
              }
              if (newIds.length) {
                const lbcur = await (await fetch(`${API_BASE}/lorebooks/${lbId}`)).json();
                const ids = [...(lbcur.entry_ids||[]), ...newIds];
                await updateLorebook(lbId, { entry_ids: ids });
              }
              uiStore.setSuggestOpen(false);
            } catch (e) { console.error(e); alert(e.message);} }} />
        )}
        {showSOHint && (
          <section className="panel overlay" onClick={()=> setShowSOHint(false)}>
            <div className="dialog" onClick={(e)=> e.stopPropagation()}>
              <h3>Enable Structured Output?</h3>
              <p className="muted">The assistant attempted to call a tool. Structured Output improves tool reliability on Gemini models.</p>
              <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                <label><input type="checkbox" onChange={(e)=> setSuppressSOHint(e.target.checked)} /> Don't show again (this session)</label>
                <span style={{ flex: 1 }} />
                <button className="secondary" onClick={()=> setShowSOHint(false)}>Cancel</button>
                <button onClick={async ()=>{ try { await updateConfig({ structured_output: true }); setShowSOHint(false); } catch (e) { alert(String(e)); } }}>Enable</button>
              </div>
            </div>
          </section>
        )}

      </main>

      {/* Toast Notifications */}
      <div className="toast-container" aria-live="assertive" aria-atomic="true">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            {toast.message}
            <button className="toast-close" onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))} aria-label="Dismiss notification">×</button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;

function ImagesTab() {
  const [cfg, setCfg] = useState({ active: 'pollinations', pollinations: { api_key: '', model: '' }, dezgo: { api_key: '', model: '', lora_flux_1: '', lora_flux_2: '', lora_sd1_1: '', lora_sd1_2: '', transparent: false, width: '', height: '', steps: '', upscale: false } });
  const [models, setModels] = useState([]);
  const [familyFilter, setFamilyFilter] = useState('');

  useEffect(() => { (async () => { try { const c = await getConfig(); setCfg(c.images); const m = await getImageModels(c.images.active); setModels(m.models || []); const fam0 = modelFamily(c.images?.dezgo?.model); setFamilyFilter(fam0);} catch (e) { console.error(e);} })(); }, []);

  const loadModels = async (prov) => { try { const m = await getImageModels(prov); setModels(m.models || []);} catch (e) { console.error(e); setModels([]);} };

  const saveCfg = async (next) => { try { await updateConfig({ images: next }); } catch (e) { console.error(e); alert(e.message);} };

  // Helpers for Dezgo model family
  const modelFamily = (m) => {
    const s = (m || '').toLowerCase();
    if (s.includes('flux')) return 'flux';
    if (s.includes('lightning')) return 'sdxl_lightning';
    if (s.includes('sdxl')) return 'sdxl';
    return 'sd1';
  };

  const fam = modelFamily(cfg.dezgo?.model);
  const famView = familyFilter || fam;
  const familyOptions = [
    { id: 'flux', label: 'Flux' },
    { id: 'sdxl', label: 'SDXL' },
    { id: 'sdxl_lightning', label: 'SDXL Lightning' },
    { id: 'sd1', label: 'SD1' },
  ];
  const filteredModels = (models||[]).filter(m => modelFamily(m) === famView);

  return (
    <div className="config-form">
      <label>
        <span>Active Provider</span>
        <select value={cfg.active} onChange={async (e) => { const v = e.target.value; const next = { ...cfg, active: v }; setCfg(next); await saveCfg(next); }}>
          <option value="pollinations">Pollinations</option>
          <option value="dezgo">Dezgo</option>
        </select>
      </label>
      {cfg.active === 'pollinations' && (
        <>
          <label>
            <span>Model</span>
            <select value={cfg.pollinations.model || ''} onChange={async (e) => { const v = e.target.value; const next = { ...cfg, pollinations: { ...cfg.pollinations, model: v } }; setCfg(next); await saveCfg(next); }}>
              <option value="">(default)</option>
              {models.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
          </label>
          <label>
            <span>API Key</span>
            <input placeholder={cfg.pollinations.api_key_masked ? `Saved: ${cfg.pollinations.api_key_masked}` : ''} value={cfg.pollinations.api_key || ''} onChange={(e) => setCfg(c => ({ ...c, pollinations: { ...c.pollinations, api_key: e.target.value } }))} />
          </label>
        </>
      )}
      {cfg.active === 'dezgo' && (
        <>
          <label>
            <span>API Key</span>
            <input placeholder={cfg.dezgo.api_key_masked ? `Saved: ${cfg.dezgo.api_key_masked}` : ''} value={cfg.dezgo.api_key || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, api_key: e.target.value } }))} />
          </label>
          <label>
            <span>Family</span>
            <select value={famView} onChange={(e)=> setFamilyFilter(e.target.value)}>
              {familyOptions.map(o => (<option key={o.id} value={o.id}>{o.label}</option>))}
            </select>
          </label>
          <label>
            <span>Model</span>
            <select value={cfg.dezgo.model || ''} onChange={(e) => {
              const v = e.target.value; const fam = modelFamily(v);
              const next = { ...cfg, dezgo: { ...cfg.dezgo, model: v, steps: fam==='flux' ? 4 : (fam==='sdxl_lightning' ? '' : (cfg.dezgo.steps || 30)) } };
              setCfg(next); saveCfg(next);
            }}>
              <option value="">(default)</option>
              {filteredModels.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
          </label>
          <div className="muted">Family: {famView.toUpperCase()}</div>
          <div className="muted">
            {famView==='sd1' ? 'Transparent background disabled; Upscale available.' : (famView==='sdxl_lightning' ? 'Steps disabled (Lightning is fixed).' : 'Transparent background available; consider steps ~30.')}
          </div>
          {famView==='flux' && (
            <>
              <label>
                <span>Flux LORA #1 (SHA256)</span>
                <input value={cfg.dezgo.lora_flux_1 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_flux_1: e.target.value } }))} />
              </label>
              <label>
                <span>Flux LORA #2 (SHA256)</span>
                <input value={cfg.dezgo.lora_flux_2 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_flux_2: e.target.value } }))} />
              </label>
              <label>
                <span>LoRA 1 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_flux_1} value={cfg.dezgo.lora1_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora1_strength: parseFloat(e.target.value) } }))} />
              </label>
              <label>
                <span>LoRA 2 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_flux_2} value={cfg.dezgo.lora2_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora2_strength: parseFloat(e.target.value) } }))} />
              </label>
            </>
          )}
          {famView==='sd1' && (
            <>
              <label>
                <span>SD1 LORA #1 (SHA256)</span>
                <input value={cfg.dezgo.lora_sd1_1 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_sd1_1: e.target.value } }))} />
              </label>
              <label>
                <span>SD1 LORA #2 (SHA256)</span>
                <input value={cfg.dezgo.lora_sd1_2 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_sd1_2: e.target.value } }))} />
              </label>
              <label>
                <span>LoRA 1 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_sd1_1} value={cfg.dezgo.lora1_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora1_strength: parseFloat(e.target.value) } }))} />
              </label>
              <label>
                <span>LoRA 2 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_sd1_2} value={cfg.dezgo.lora2_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora2_strength: parseFloat(e.target.value) } }))} />
              </label>
            </>
          )}
          <label>
            <span>Width</span>
            <input type="number" value={cfg.dezgo.width || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, width: e.target.value } }))} />
          </label>
          <label>
            <span>Height</span>
            <input type="number" value={cfg.dezgo.height || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, height: e.target.value } }))} />
          </label>
          {famView!=='sdxl_lightning' && (
            <label>
              <span>Steps</span>
              <input type="number" value={cfg.dezgo.steps || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, steps: e.target.value } }))} />
            </label>
          )}
          <label>
            <span>Transparent Background</span>
            <input type="checkbox" disabled={famView === 'sd1'} checked={!!cfg.dezgo.transparent} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, transparent: e.target.checked } }))} />
          </label>
          <label>
            <span>Upscale</span>
            <input type="checkbox" disabled={famView !== 'sd1'} checked={!!cfg.dezgo.upscale} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, upscale: e.target.checked } }))} />
          </label>
        </>
      )}
      <div className="row" style={{ gridColumn: '1 / -1' }}>
        <button onClick={async () => { try { const current = (await getConfig()).images; const changes = JSON.stringify(cfg) !== JSON.stringify(current); if (changes) { if (!window.confirm('Images config.json will be updated. Proceed?')) return; } await saveCfg(cfg); alert('Saved'); } catch (e) { console.error(e); alert(e.message); } }}>Save Image Settings</button>
      </div>
    </div>
  );
}

function PromptsTab() {
  const [all, setAll] = useState([]);
  const [active, setActive] = useState([]);
  const [newText, setNewText] = useState('');
  const [system, setSystem] = useState({ lore_suggest: '', image_summary: '', main: '', tool_call: '' });
  const [vars, setVars] = useState({});
  const [newVarName, setNewVarName] = useState('');
  const [newVarValue, setNewVarValue] = useState('');
  const [showPH, setShowPH] = useState(false);
  useEffect(() => { (async () => { try { const d = await getPrompts(); setAll(d.all || []); setActive(d.active || []); setSystem(d.system || { lore_suggest: '', image_summary: '' }); setVars(d.variables || {});} catch (e) { console.error(e);} })(); }, []);
  const save = async (na = all, aa = active, sys = system, vs = vars) => { try { await savePrompts({ all: na, active: aa, system: sys, variables: vs }); setAll(na); setActive(aa); setSystem(sys); setVars(vs);} catch (e) { console.error(e); alert(e.message);} };
  const toggleActive = (txt) => { const aa = active.includes(txt) ? active.filter(x=>x!==txt) : [...active, txt]; save(all, aa); };
  const add = () => { const t = newText.trim(); if (!t) return; const na = [...all, t]; setNewText(''); save(na, active); };
  const remove = (txt) => { const na = all.filter(x=>x!==txt); const aa = active.filter(x=>x!==txt); save(na, aa); };
  return (
    <>
    <div className="config-form" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      <div style={{ gridColumn: '1 / -1' }}>
        <h3>System Prompts</h3>
        <div className="muted">These prompts guide built-in tools. <a href="#" onClick={(e)=>{ e.preventDefault(); setShowPH(true); }}>Use placeholders</a>.</div>
      </div>
      <label>
        <span>Main System Prompt</span>
        <textarea rows={4} value={system.main || ''} onChange={(e)=> setSystem(s => ({ ...s, main: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="{{tool_call_prompt}}, {{user_persona}}, {{character_description}}, {{tool_list}}, {{conversation}}" />
      </label>
      <label>
        <span>Tool Call Prompt</span>
        <textarea rows={4} value={system.tool_call || ''} onChange={(e)=> setSystem(s => ({ ...s, tool_call: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="Describe structured output JSON with toolCalls array." />
      </label>
      <label>
        <span>Lorebook suggestion prompt</span>
        <textarea rows={4} value={system.lore_suggest} onChange={(e)=> setSystem(s => ({ ...s, lore_suggest: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="Use {{conversation}} and {{existing_keywords}}" />
      </label>
      <label>
        <span>Image generation prompt</span>
        <textarea rows={4} value={system.image_summary} onChange={(e)=> setSystem(s => ({ ...s, image_summary: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="Use {{conversation}}" />
      </label>
      <div style={{ gridColumn: '1 / -1', marginTop: 8 }}>
        <h3>Variables</h3>
        <div className="muted">Define reusable snippets that replace tags like <code>{'{'}{'{'}company{'}'}{'}'}</code> anywhere the LLM sees them.</div>
      </div>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="name (e.g., site)" value={newVarName} onChange={(e)=> setNewVarName(e.target.value)} />
        <input placeholder="value" value={newVarValue} onChange={(e)=> setNewVarValue(e.target.value)} />
        <button className="secondary" onClick={()=>{ const n = newVarName.trim(); if (!n) return; const vs = { ...vars, [n]: newVarValue }; setNewVarName(''); setNewVarValue(''); save(all, active, system, vs); }}>Add</button>
      </div>
      <div className="row" style={{ display: 'block', marginTop: 8 }}>
        {Object.entries(vars).map(([k,v]) => (
          <div key={k} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <code style={{ width: 160 }}>{`{{${k}}}`}</code>
            <input style={{ flex: 1 }} value={v} onChange={(e)=> { const vs = { ...vars, [k]: e.target.value }; setVars(vs); }} onBlur={()=> save(all, active, system, vars)} />
            <button className="secondary" onClick={()=>{ const vs = { ...vars }; delete vs[k]; save(all, active, system, vs); }}>Delete</button>
          </div>
        ))}
      </div>
      <div style={{ gridColumn: '1 / -1', marginTop: 8 }}>
        <h3>General Prompts</h3>
        <div className="muted">Short, reusable prompts that can be toggled on to influence replies globally.</div>
      </div>
      <label>
        <span>New Prompt</span>
        <div className="row" style={{ gap: 8 }}>
          <input value={newText} onChange={(e)=> setNewText(e.target.value)} placeholder="Short prompt text to include in system context" />
          <button className="secondary" onClick={add}>Add</button>
        </div>
      </label>
      <div className="row" style={{ display: 'block' }}>
        {(all||[]).map((p, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <input type="checkbox" checked={active.includes(p)} onChange={()=> toggleActive(p)} />
            <span style={{ flex: 1 }}>{p}</span>
            <button className="secondary" onClick={()=> remove(p)}>Delete</button>
          </div>
        ))}
      </div>
    </div>
    {showPH && (
      <section className="panel overlay" onClick={()=> setShowPH(false)}>
        <div className="dialog" onClick={(e)=> e.stopPropagation()}>
          <h3>Available placeholders</h3>
          <ul className="muted">
            <li><code>{'{{conversation}}'}</code>: recent conversation window</li>
            <li><code>{'{{existing_keywords}}'}</code>: active lore keywords</li>
            <li><code>{'{{tool_call_prompt}}'}</code>: tool call guidance</li>
            <li><code>{'{{user_persona}}'}</code>: user persona summary</li>
            <li><code>{'{{character_description}}'}</code>: character description/personality</li>
            <li><code>{'{{tool_list}}'}</code>: enabled tools list</li>
            {Object.keys(vars).map(k => (<li key={k}><code>{`{{${k}}}`}</code>: variable</li>))}
          </ul>
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="secondary" onClick={()=> setShowPH(false)}>Close</button>
          </div>
        </div>
      </section>
    )}
    </>
  );
}

function ToolsTab() {
  const [servers, setServers] = useState([]);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [catalog, setCatalog] = useState([]);
  const [selIdx, setSelIdx] = useState('');
  useEffect(() => { (async () => { try { const d = await getMcpServers(); setServers(d.servers || []); const c = await getMcpAwesome(); setCatalog(c.items || []);} catch (e) { console.error(e);} })(); }, []);
  const save = async (list) => { try { await saveMcpServers({ servers: list }); setServers(list);} catch (e) { console.error(e); alert('Save failed'); } };
  return (
    <div className="config-form">
      <p className="muted">Register MCP servers the assistant can call in future sessions.</p>
      <label>
        <span>Catalog</span>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <select value={selIdx} onChange={(e)=> setSelIdx(e.target.value)}>
            <option value="">(select server)</option>
            {catalog.map((it, i) => (<option key={i} value={i}>{it.name}</option>))}
          </select>
          {selIdx!=='' && (
            <>
              <button className="secondary" onClick={()=>{ const it=catalog[parseInt(selIdx,10)]; if (!it) return; const list=[...servers,{ name: it.name, url: it.url }]; save(list); }}>Add Server</button>
              <a className="secondary" href={catalog[parseInt(selIdx,10)]?.url} target="_blank" rel="noreferrer">Open</a>
            </>
          )}
        </div>
        {selIdx!=='' && (
          <div className="muted" style={{ marginTop: 6 }}>{catalog[parseInt(selIdx,10)]?.description}</div>
        )}
      </label>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="Name" value={name} onChange={(e)=> setName(e.target.value)} />
        <input placeholder="URL or command" value={url} onChange={(e)=> setUrl(e.target.value)} />
        <button onClick={()=>{ const n = name.trim(); const u = url.trim(); if (!n || !u) return; const list = [...servers, { name: n, url: u }]; save(list); setName(''); setUrl(''); }}>Add</button>
      </div>
      <div style={{ marginTop: 8 }}>
        {servers.map((s, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <span style={{ width: 180 }}>{s.name}</span>
            <span style={{ flex: 1 }} className="muted">{s.url}</span>
            <button className="secondary" onClick={()=>{ const list = servers.filter((_,idx)=> idx!==i); save(list); }}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function ToolsOverlay({ onClose }) {
  const [enabled, setEnabled] = useState({ phone: false, image_gen: false, lore_suggest: false });
  const [structured, setStructured] = useState(false);
  const [notified, setNotified] = useState(false);
  const [servers, setServers] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [selIdx, setSelIdx] = useState('');
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  useEffect(() => { (async () => { try { const cfg = await getConfig(); setStructured(!!cfg.structured_output); const cid = cfg.active_character_id; const t = await (await fetch(`${API_BASE}/tools/settings${cid?`?character_id=${cid}`:''}`)).json(); setEnabled(t.enabled || {}); } catch (e) { console.error(e);} })(); }, []);
  const save = async (en) => { try { const cfg = await getConfig(); const cid = cfg.active_character_id; await fetch(`${API_BASE}/tools/settings${cid?`?character_id=${cid}`:''}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: en }) }); setEnabled(en); if (!notified && (en.phone||en.image_gen||en.lore_suggest) && !structured) { alert('Enabling tools benefits from Structured Output. You can toggle it in Connection settings.'); setNotified(true);} } catch (e) { console.error(e); alert('Save failed'); } };
  useEffect(() => { (async () => { try { const d = await getMcpServers(); setServers(d.servers || []); const c = await getMcpAwesome(); setCatalog(c.items || []);} catch (e) { console.error(e);} })(); }, []);
  const saveServers = async (list) => { try { await saveMcpServers({ servers: list }); setServers(list);} catch (e) { console.error(e); alert('Save failed'); } };
  return (
    <div className="config-form">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={!!enabled.phone} onChange={(e)=> save({ ...enabled, phone: e.target.checked })} />
          Phone Panel <em>(phone_url)</em>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={!!enabled.image_gen} onChange={(e)=> save({ ...enabled, image_gen: e.target.checked })} />
          Image Generation <em>(image_request)</em>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={!!enabled.lore_suggest} onChange={(e)=> save({ ...enabled, lore_suggest: e.target.checked })} />
          Lore Suggest <em>(lore_suggestions)</em>
        </label>
      </div>
      <p className="muted" style={{ marginTop: 12 }}>When tools are enabled, the assistant receives concise instructions about each tool. For Gemini models, enable "Structured Output" in Connection to get reliable tool-usage responses.</p>
      <hr />
      <h3>MCP Servers</h3>
      <label>
        <span>Catalog</span>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <select value={selIdx} onChange={(e)=> setSelIdx(e.target.value)}>
            <option value="">(select server)</option>
            {catalog.map((it, i) => (<option key={i} value={i}>{it.name}</option>))}
          </select>
          {selIdx!=='' && (
            <>
              <button className="secondary" onClick={()=>{ const it=catalog[parseInt(selIdx,10)]; if (!it) return; const list=[...servers,{ name: it.name, url: it.url }]; saveServers(list); }}>Add Server</button>
              <a className="secondary" href={catalog[parseInt(selIdx,10)]?.url} target="_blank" rel="noreferrer">Open</a>
            </>
          )}
        </div>
        {selIdx!=='' && (
          <div className="muted" style={{ marginTop: 6 }}>{catalog[parseInt(selIdx,10)]?.description}</div>
        )}
      </label>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="Name" value={name} onChange={(e)=> setName(e.target.value)} />
        <input placeholder="URL or command" value={url} onChange={(e)=> setUrl(e.target.value)} />
        <button onClick={()=>{ const n = name.trim(); const u = url.trim(); if (!n || !u) return; const list = [...servers, { name: n, url: u }]; saveServers(list); setName(''); setUrl(''); }}>Add</button>
      </div>
      <div style={{ marginTop: 8 }}>
        {servers.map((s, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 6, padding: 8, background: 'var(--panel)', borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: 14 }}>{s.name}</strong>
              <button className="secondary" onClick={()=>{ const list = servers.filter((_,idx)=> idx!==i); saveServers(list); }}>Remove</button>
            </div>
            <div className="muted" style={{ fontSize: 12, wordBreak: 'break-all' }}>{s.url}</div>
          </div>
        ))}
      </div>
      <div className="row" style={{ justifyContent: 'flex-end' }}>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function ActiveLorebooks({ lorebooks }) {
  const [activeIds, setActiveIds] = useState([]);
  const [selId, setSelId] = useState('');
  useEffect(() => { (async () => { try { const cfg = await getConfig(); setActiveIds(cfg.active_lorebook_ids || []);} catch (e) { console.error(e);} })(); }, []);
  const add = async () => { try { const id = parseInt(selId,10); if (!id) return; if (!activeIds.includes(id)) { const list = [...activeIds, id]; setActiveIds(list); await updateConfig({ active_lorebook_ids: list }); } } catch (e) { console.error(e); alert(e.message);} };
  const remove = async (id) => { try { const list = activeIds.filter(x => x!==id); setActiveIds(list); await updateConfig({ active_lorebook_ids: list }); } catch (e) { console.error(e); alert(e.message);} };
  return (
    <div className="row" style={{ gap: 8, alignItems: 'center' }}>
      <span className="muted">Active Lorebooks</span>
      <select value={selId} onChange={(e)=> setSelId(e.target.value)}>
        <option value="">(select)</option>
        {lorebooks.map(lb => (<option key={lb.id} value={lb.id}>{lb.name}</option>))}
      </select>
      <button className="secondary" onClick={add}>➕</button>
      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
        {activeIds.map(id => { const lb = lorebooks.find(x => x.id===id); return (
          <span key={id} className="secondary" style={{ padding: '4px 8px', borderRadius: 6 }}>{lb ? lb.name : `#${id}`} <button className="secondary" onClick={() => remove(id)}>➖</button></span>
        ); })}
      </div>
    </div>
  );
}

function AdvancedTab() {
  const [raw, setRaw] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => { (async () => {
    try {
      setLoading(true);
      const r = await fetch(`${API_BASE}/config/raw`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setRaw(JSON.stringify(data, null, 2));
    } catch (e) { console.error(e); setError(String(e)); setRaw(''); }
    finally { setLoading(false); }
  })(); }, []);
  return (
    <div>
      <p className="muted">Full settings.json (copy/share):</p>
      {loading ? (
        <div className="muted">Loading settings…</div>
      ) : error ? (
        <div className="muted">Unable to load settings: {error}</div>
      ) : (
        <textarea rows={16} style={{ width: '100%' }} value={raw} onChange={(e)=>setRaw(e.target.value)} />
      )}
      <div className="row" style={{ marginTop: 8 }}>
        <button className="secondary" onClick={() => {
          const blob = new Blob([raw], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = 'settings.json'; a.click(); URL.revokeObjectURL(url);
        }}>Export settings.json</button>
        <label className="secondary" style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>
          Import settings.json
          <input type="file" accept="application/json,.json" style={{ display: 'none' }} onChange={async (e) => {
            const f = e.target.files?.[0]; if (!f) return;
            try { const text = await f.text(); const data = JSON.parse(text); const r = await fetch(`${API_BASE}/config/raw`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!r.ok) throw new Error('Import failed'); alert('Imported. Reloading...'); location.reload(); } catch (err) { console.error(err); alert(err.message); } finally { e.target.value=''; }
          }} />
        </label>
        <button onClick={async ()=>{ try { const data = JSON.parse(raw); const r = await fetch(`${API_BASE}/config/raw`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!r.ok) throw new Error('Save failed'); alert('Saved. Reloading...'); location.reload(); } catch (e) { console.error(e); alert(e.message);} }}>Save settings.json</button>
      </div>
      <hr />
      <p className="muted">Advanced settings</p>
    </div>
  );
}

function ThemesManager() {
  const [names, setNames] = useState([]);
  const [sel, setSel] = useState('');
  const [theme, setTheme] = useState(null);
  const load = async () => { try { const r = await fetch(`${API_BASE}/themes`); if (r.ok) { const d = await r.json(); setNames(d.names || []); } } catch (e) { console.error(e);} };
  useEffect(() => { load(); }, []);
  return (
    <div className="row" style={{ gap: 8 }}>
      <select value={sel} onChange={(e)=> setSel(e.target.value)}>
        <option value="">(select)</option>
        {names.map(n => (<option key={n} value={n}>{n}</option>))}
      </select>
      <button className="secondary" onClick={async ()=>{ if (!sel) return; try { const r = await fetch(`${API_BASE}/themes/${sel}`); if (!r.ok) throw new Error('Load failed'); const t = await r.json(); await fetch(`${API_BASE}/config`, { method: 'PUT', headers: { 'Content-Type':'application/json' }, body: JSON.stringify({ theme: t }) }); try { const root = document.documentElement; root.style.setProperty('--primary', t.primary); root.style.setProperty('--panel', t.secondary); root.style.setProperty('--text', t.text1); root.style.setProperty('--muted', t.text2); root.style.setProperty('--assistant', t.highlight); root.style.setProperty('--bg', t.lowlight);} catch (e) { console.error(e);} alert('Theme loaded'); } catch (e) { console.error(e); alert(e.message);} }}>Load Theme</button>
      <button onClick={async ()=>{ const name = prompt('Save theme as:'); if (!name) return; try { const cfg = await getConfig(); const t = cfg.theme || {}; const r = await fetch(`${API_BASE}/themes`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, theme: t })}); if (!r.ok) throw new Error('Save theme failed'); alert('Theme saved'); load(); } catch (e) { console.error(e); alert(e.message);} }}>Save Current Theme</button>
    </div>
  );
}

function AppearanceTab() {
  const [theme, setTheme] = useState({ primary: '#2563eb', secondary: '#374151', text1: '#e5e7eb', text2: '#cbd5e1', highlight: '#10b981', lowlight: '#111827', phone_style: 'classic' });
  const [presetThemes, setPresetThemes] = useState([
    { name: 'Default', theme: { primary: '#2563eb', secondary: '#374151', text1: '#e5e7eb', text2: '#cbd5e1', highlight: '#10b981', lowlight: '#111827' } },
    { name: 'Dark', theme: { primary: '#8b5cf6', secondary: '#1f2937', text1: '#f9fafb', text2: '#d1d5db', highlight: '#f59e0b', lowlight: '#111827' } },
    { name: 'Light', theme: { primary: '#3b82f6', secondary: '#f3f4f6', text1: '#111827', text2: '#6b7280', highlight: '#059669', lowlight: '#f9fafb' } },
    { name: 'Forest', theme: { primary: '#059669', secondary: '#064e3b', text1: '#ecfdf5', text2: '#a7f3d0', highlight: '#f59e0b', lowlight: '#022c22' } },
    { name: 'Ocean', theme: { primary: '#0891b2', secondary: '#164e63', text1: '#ecfeff', text2: '#a5f3fc', highlight: '#f97316', lowlight: '#0c4a6e' } },
    { name: 'Rose', theme: { primary: '#db2777', secondary: '#5b21b6', text1: '#fef2f2', text2: '#fecaca', highlight: '#eab308', lowlight: '#581c87' } }
  ]);

  useEffect(() => { (async () => { try { const r = await getConfig(); if (r.theme) setTheme(r.theme);} catch (e) { console.error(e);} })(); }, []);
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--primary', theme.primary);
    root.style.setProperty('--panel', theme.secondary);
    root.style.setProperty('--text', theme.text1);
    root.style.setProperty('--muted', theme.text2);
    root.style.setProperty('--assistant', theme.highlight);
    root.style.setProperty('--bg', theme.lowlight);
  }, [theme]);

  const save = async (next) => { setTheme(next); try { await updateConfig({ theme: next }); try { window.dispatchEvent(new CustomEvent('coolchat:themeUpdate', { detail: next })); } catch {} } catch (e) { console.error(e); alert(e.message);} };

  const suggest = async () => {
    try {
      const r = await fetch(`${API_BASE}/theme/suggest`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ primary: theme.primary }) });
      if (!r.ok) throw new Error('Suggest failed');
      const { colors } = await r.json();
      if (colors.length >= 5) {
        const next = { ...theme, secondary: colors[0], text1: colors[1], text2: colors[2], highlight: colors[3], lowlight: colors[4] };
        await save(next);
      }
    } catch (e) { console.error(e); alert(e.message);}
  };

  const applyPreset = async (preset) => {
    await save({ ...theme, ...preset.theme });
  };

  const swapBGColors = async () => {
    const inverted = {
      ...theme,
      secondary: theme.lowlight,
      lowlight: theme.secondary,
      text1: theme.text1,
      text2: theme.text2
    };
    await save(inverted);
  };

  const Color = ({ label, keyName, withThink }) => (
    <label>
      <span>{label}</span>
      <div className="row color-row" style={{ gap: 8, alignItems: 'center' }}>
        <input className="color-swatch" type="color" value={theme[keyName]} onChange={async (e) => { await save({ ...theme, [keyName]: e.target.value }); }} />
        <input style={{ flex: 1 }} value={theme[keyName]} onChange={async (e) => { await save({ ...theme, [keyName]: e.target.value }); }} />
        {withThink && (<button className="think" title="AI suggests complementary colors for this primary" onClick={suggest}>💭</button>)}
      </div>
    </label>
  );

  return (
    <div className="config-form">
      <div className="theme-preview" style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12,
        marginBottom: 16,
        padding: 12,
        background: 'var(--panel)',
        borderRadius: 8,
        border: '1px solid var(--muted)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ background: 'var(--primary)', width: 40, height: 20, borderRadius: 4, margin: '0 auto 8px' }}></div>
          <small style={{ color: 'var(--text)' }}>Primary</small>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ background: 'var(--bg)', width: 40, height: 20, borderRadius: 4, border: '1px solid var(--secondary)', margin: '0 auto 8px' }}></div>
          <small style={{ color: 'var(--text)' }}>Background</small>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ background: 'var(--panel)', width: 40, height: 20, borderRadius: 4, border: '1px solid var(--muted)', margin: '0 auto 8px' }}></div>
          <small style={{ color: 'var(--text)' }}>Panel</small>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ background: 'var(--assistant)', width: 40, height: 20, borderRadius: 4, margin: '0 auto 8px' }}></div>
          <small style={{ color: 'var(--text)' }}>Assistant</small>
        </div>
      </div>

      <label style={{ gridColumn: '1 / -1' }}>
        <span>Preset Themes</span>
        <div className="row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
          {presetThemes.map((preset, index) => (
            <button
              key={index}
              className="secondary theme-btn"
              style={{
                background: `linear-gradient(45deg, ${preset.theme.primary}, ${preset.theme.secondary})`,
                color: preset.theme.text1,
                border: 'none',
                borderRadius: 6,
                padding: '6px 12px',
                fontSize: 12,
                cursor: 'pointer'
              }}
              onClick={() => applyPreset(preset)}
              title={`Apply ${preset.name} theme`}
            >
              {preset.name}
            </button>
          ))}
          <button className="secondary" onClick={swapBGColors} title="Swap background colors for high contrast">🔄 Invert BG</button>
        </div>
      </label>

      <Color label="Primary" keyName="primary" withThink={true} />
      <Color label="Secondary" keyName="secondary" />
      <Color label="Text 1" keyName="text1" />
      <Color label="Text 2" keyName="text2" />
      <Color label="Highlight" keyName="highlight" />
      <Color label="Lowlight" keyName="lowlight" />

      <label>
        <span>Phone Style</span>
        <select value={theme.phone_style || 'classic'} onChange={async (e)=> { const next = { ...theme, phone_style: e.target.value }; await save(next); try { window.dispatchEvent(new CustomEvent('coolchat:phoneStyle', { detail: next.phone_style })); } catch {} }}>
          <option value="classic">Classic</option>
          <option value="modern">Modern</option>
          <option value="iphone">iPhone</option>
          <option value="cyberpunk">Cyberpunk</option>
        </select>
      </label>

      <label style={{ gridColumn: '1 / -1' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          Background Animations
          <small style={{ color: 'var(--muted)', fontWeight: 'normal' }}>(Multiple allowed)</small>
        </span>
        <div className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <select id="anim-select" style={{ flex: 1 }}>
            <option value="gradient_flow">Gradient Flow</option>
            <option value="floating_squares">Floating Squares</option>
            <option value="waves">Ocean Waves</option>
            <option value="neon_rain">Neon Rain</option>
            <option value="matrix">Matrix Code</option>
            <option value="particles">Floating Particles</option>
            <option value="geometric">Geometric Shapes</option>
          </select>
          <button className="secondary" onClick={() => {
            try {
              const sel = document.querySelector('#anim-select');
              const id = sel?.value;
              if (!id || id === '') return;
              const list = Array.isArray(theme.background_animations) ? [...theme.background_animations] : [];
              if (!list.includes(id) && list.length < 3) { // Limit to 3 animations max
                save({ ...theme, background_animations: [...list, id] });
              } else if (list.length >= 3) {
                alert('Maximum 3 background animations allowed');
              }
            } catch (e) { console.error(e); }
          }}>+ Add</button>
        </div>
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {(theme.background_animations||[]).map((id, i) => (
            <span key={i} className="tag" style={{
              padding: '4px 8px',
              borderRadius: 12,
              background: 'var(--panel)',
              border: '1px solid var(--muted)',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 4
            }}>
              {id}
              <button className="remove-tag" onClick={() => {
                const list = (theme.background_animations||[]).filter(x => x!==id);
                save({ ...theme, background_animations: list });
              }} style={{
                border: 'none',
                background: 'transparent',
                color: 'var(--muted)',
                cursor: 'pointer',
                fontSize: 14,
                lineHeight: 1
              }}>×</button>
            </span>
          ))}
        </div>
      </label>

      <hr />
      <div style={{ gridColumn: '1 / -1' }}>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <span><strong>Saved Themes</strong></span>
          <button className="secondary" onClick={async () => {
            const name = prompt('Export current theme as:');
            if (name && name.trim()) {
              await fetch(`${API_BASE}/themes`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name: name.trim(), theme: { ...theme } })});
              alert('Theme exported: ' + name.trim());
            }
          }} title="Export current theme to saved themes">📤 Export</button>
        </div>
        <div style={{ marginTop: 8 }}>
          <ThemesManager />
        </div>
      </div>
    </div>
  );
}

function SuggestLoreModal({ suggestions, onClose, onApply }) {
  console.log('[DEBUG] SuggestLoreModal received suggestions:', suggestions);
  const [rows, setRows] = useState(() => (suggestions || []).map(s => ({ include: true, keyword: s.keyword || '', content: s.content || '' })));
  console.log('[DEBUG] SuggestLoreModal rows initialized:', rows);
  const [lbOptions, setLbOptions] = useState([]);
  const [selLb, setSelLb] = useState('');
  useEffect(() => { (async () => { try { const cfg = await getConfig(); const actives = cfg.active_lorebook_ids || []; if (actives.length) { const lbs = await listLorebooks(); const opts = lbs.filter(x => actives.includes(x.id)).map(x => ({ id: x.id, name: x.name })); setLbOptions(opts); setSelLb(String(opts[0]?.id || '')); } } catch (e) { console.error(e);} })(); }, []);
  return (
    <section className="panel overlay">
      <h2>Lore Suggestions</h2>
      {lbOptions.length > 1 && (
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <span className="muted">Target Lorebook</span>
          <select value={selLb} onChange={(e)=> setSelLb(e.target.value)}>
            {lbOptions.map(o => (<option key={o.id} value={o.id}>{o.name}</option>))}
          </select>
        </div>
      )}
      <div className="char-list" style={{ maxHeight: 360, overflow: 'auto' }}>
        {rows.map((r, i) => (
          <div key={i} className="char-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
            <div className="row" style={{ gap: 8, alignItems: 'center' }}>
              <input type="checkbox" checked={r.include} onChange={(e)=> setRows(arr => arr.map((x,idx)=> idx===i? { ...x, include: e.target.checked }: x))} />
              <input placeholder="Keyword" value={r.keyword} onChange={(e)=> setRows(arr => arr.map((x,idx)=> idx===i? { ...x, keyword: e.target.value }: x))} />
            </div>
            <textarea rows={3} placeholder="Content" value={r.content} onChange={(e)=> setRows(arr => arr.map((x,idx)=> idx===i? { ...x, content: e.target.value }: x))} />
          </div>
        ))}
      </div>
      <div className="row" style={{ justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
        <button className="secondary" onClick={onClose}>Cancel</button>
        <button onClick={()=> onApply(rows, selLb ? parseInt(selLb,10) : null)}>Add Selected</button>
      </div>
    </section>
  );
}

function ChatManager({ sessionId, setSessionId, onClose }) {
  const [sessions, setSessions] = useState([]);
  const [newName, setNewName] = useState('');
  const load = async () => { try { const d = await listChats(); setSessions(d.sessions || []);} catch (e) { console.error(e);} };
  useEffect(() => { load(); }, []);
  return (
    <div className="config-form">
      <div className="row" style={{ gap: 8, alignItems: 'center' }}>
        <select value={sessionId} onChange={async (e)=> { const id = e.target.value; setSessionId(id); }}>
          {[...sessions].map(id => (<option key={id} value={id}>{id}</option>))}
        </select>
        <button className="secondary" onClick={load}>Refresh</button>
        <button className="secondary" onClick={async ()=>{ try { await resetChat(sessionId); await load(); setSessionId('default'); } catch (e) { alert(e.message);} }}>Reset</button>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>
      <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <input placeholder="New session id (e.g., 2025-01-01T12:00)" value={newName} onChange={(e)=> setNewName(e.target.value)} style={{ flex: 1 }} />
        <button onClick={async ()=>{ const id = (newName||'').trim() || String(Date.now()); if (!sessions.includes(id)) setSessions(s => [...s, id]); setSessionId(id); setNewName(''); }}>New</button>
      </div>
    </div>
  );
}

function CharacterEditor({ character, onClose, onSave, onThink, lorebooks }) {
  const [draft, setDraft] = useState(() => ({
    name: character?.name || '',
    description: character?.description || '',
    avatar_url: character?.avatar_url || '',
    first_message: character?.first_message || '',
    alternate_greetings: (character?.alternate_greetings || []).join(', '),
    scenario: character?.scenario || '',
    system_prompt: character?.system_prompt || '',
    personality: character?.personality || '',
    mes_example: character?.mes_example || '',
    creator_notes: character?.creator_notes || '',
    tags: (character?.tags || []).join(', '),
    post_history_instructions: character?.post_history_instructions || '',
    lorebook_ids: character?.lorebook_ids || [],
    image_prompt_prefix: character?.image_prompt_prefix || '',
    image_prompt_suffix: character?.image_prompt_suffix || '',
  }));
  const [thinkingField, setThinkingField] = useState(null);
  const [painting, setPainting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const think = async (field) => {
    try {
      setThinkingField(field);
      const val = await onThink(field, draft);
      setDraft((d) => ({ ...d, [field]: val }));
    } finally {
      setThinkingField(null);
    }
  };

  return (
    <div className="modal" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h2>{character ? 'Edit Character' : 'New Character'}</h2>
        <div className="editor-grid">
          <span className="label">Name</span>
          <div><input value={draft.name} onChange={(e) => setDraft(d => ({ ...d, name: e.target.value }))} /> <button className="think" onClick={() => think('name')}>💭</button></div>
          <span className="label">Avatar</span>
          <div>
            {draft.avatar_url && (
              <img src={draft.avatar_url} alt="Avatar preview" style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8, marginRight: 8, border: '1px solid #1f2937' }} />
            )}
            <input type="file" accept="image/*" onChange={async (e) => {
              const f = e.target.files?.[0]; if (!f) return;
              try {
                setUploading(true);
                const fd = new FormData(); fd.append('file', f);
                const res = await fetch(`${API_BASE}/characters/upload_avatar`, { method: 'POST', body: fd });
                if (!res.ok) throw new Error('Upload failed');
                const data = await res.json();
                setDraft(d => ({ ...d, avatar_url: data.avatar_url }));
              } catch (err) { alert(err.message); } finally { setUploading(false); e.target.value = ''; }
            }} />
            <button className={`paint ${painting ? 'thinking' : ''}`} onClick={async () => {
              try {
                setPainting(true);
                const res = await fetch(`${API_BASE}/characters/generate_avatar`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ character: draft }),
                });
                if (!res.ok) throw new Error('Generate failed');
                const data = await res.json();
                setDraft(d => ({ ...d, avatar_url: data.avatar_url }));
              } catch (err) { alert(err.message); } finally { setPainting(false); }
            }}>🖌️</button>
          </div>
          <span className="label">Description</span>
          <div><textarea rows={3} value={draft.description} onChange={(e) => setDraft(d => ({ ...d, description: e.target.value }))} /> <button className={`think ${thinkingField==='description'?'thinking':''}`} onClick={() => think('description')}>💭</button></div>
          <span className="label">First Message</span>
          <div><textarea rows={3} value={draft.first_message} onChange={(e) => setDraft(d => ({ ...d, first_message: e.target.value }))} /> <button className={`think ${thinkingField==='first_message'?'thinking':''}`} onClick={() => think('first_message')}>💭</button></div>
          <span className="label">Alternate Greetings (comma)</span>
          <div><input value={draft.alternate_greetings} onChange={(e) => setDraft(d => ({ ...d, alternate_greetings: e.target.value }))} /> <button className={`think ${thinkingField==='alternate_greetings'?'thinking':''}`} onClick={() => think('alternate_greetings')}>💭</button></div>
          <span className="label">Scenario</span>
          <div><textarea rows={3} value={draft.scenario} onChange={(e) => setDraft(d => ({ ...d, scenario: e.target.value }))} /> <button className={`think ${thinkingField==='scenario'?'thinking':''}`} onClick={() => think('scenario')}>💭</button></div>
          <span className="label">System Prompt</span>
          <div><textarea rows={3} value={draft.system_prompt} onChange={(e) => setDraft(d => ({ ...d, system_prompt: e.target.value }))} /> <button className={`think ${thinkingField==='system_prompt'?'thinking':''}`} onClick={() => think('system_prompt')}>💭</button></div>
          <span className="label">Personality</span>
          <div><textarea rows={3} value={draft.personality} onChange={(e) => setDraft(d => ({ ...d, personality: e.target.value }))} /> <button className={`think ${thinkingField==='personality'?'thinking':''}`} onClick={() => think('personality')}>💭</button></div>
          <span className="label">Message Example</span>
          <div><textarea rows={3} value={draft.mes_example} onChange={(e) => setDraft(d => ({ ...d, mes_example: e.target.value }))} /> <button className={`think ${thinkingField==='mes_example'?'thinking':''}`} onClick={() => think('mes_example')}>💭</button></div>
          <span className="label">Creator Notes</span>
          <div><textarea rows={3} value={draft.creator_notes} onChange={(e) => setDraft(d => ({ ...d, creator_notes: e.target.value }))} /> <button className={`think ${thinkingField==='creator_notes'?'thinking':''}`} onClick={() => think('creator_notes')}>💭</button></div>
          <span className="label">Prepend to image prompts</span>
          <div><input value={draft.image_prompt_prefix} onChange={(e) => setDraft(d => ({ ...d, image_prompt_prefix: e.target.value }))} /> <button className={`think ${thinkingField==='image_prompt_prefix'?'thinking':''}`} onClick={() => think('image_prompt_prefix')}>💭</button></div>
          <span className="label">Append to image prompts</span>
          <div><input value={draft.image_prompt_suffix} onChange={(e) => setDraft(d => ({ ...d, image_prompt_suffix: e.target.value }))} /> <button className={`think ${thinkingField==='image_prompt_suffix'?'thinking':''}`} onClick={() => think('image_prompt_suffix')}>💭</button></div>
          <span className="label">Tags (comma)</span>
          <div><input value={draft.tags} onChange={(e) => setDraft(d => ({ ...d, tags: e.target.value }))} /></div>
          <span className="label">Post-History Instructions</span>
          <div><textarea rows={3} value={draft.post_history_instructions} onChange={(e) => setDraft(d => ({ ...d, post_history_instructions: e.target.value }))} /> <button className={`think ${thinkingField==='post_history_instructions'?'thinking':''}`} onClick={() => think('post_history_instructions')}>💭</button></div>
          <span className="label">Lorebook</span>
          <div>
            <select value={draft.lorebook_ids[0] || ''} onChange={(e) => {
              const id = e.target.value ? [parseInt(e.target.value,10)] : [];
              setDraft(d => ({ ...d, lorebook_ids: id }));
            }}>
              <option value="">-- None --</option>
              {lorebooks.map(lb => (<option key={lb.id} value={lb.id}>{lb.name}</option>))}
            </select>
          </div>
        </div>
        <div className="row" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="secondary" onClick={onClose}>Cancel</button>
          <button onClick={() => {
            const payload = {
              ...draft,
              alternate_greetings: draft.alternate_greetings.split(',').map(s => s.trim()).filter(Boolean),
              tags: draft.tags.split(',').map(s => s.trim()).filter(Boolean),
            };
            onSave(payload);
          }}>Save</button>
        </div>
      </div>
    </div>
  );
}


