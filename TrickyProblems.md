# Tricky Problems Encountered and Solutions

## Problem 1: Messages Disappearing on Subsequent Submissions

### Description
1. User submits message (e.g., "hello")
2. State updates correctly: `[ {user} ]`
3. LLM responds, assistant message added: `[ {user}, {assistant} ]`
4. User submits second message
5. State overwrites to `[ {user} ]` instead of `[ {user1}, {assistant}, {user2} ]`
6. Previous conversation history lost, similar to resetting state on each submit

### Root Cause
The `onSubmit` function in `App.jsx` was calling:
```javascript
chat.setMessages([ { role: 'user', content: trimmed } ]);  // Overwrites array
```
Instead of:
```javascript
chat.setMessages([...chat.messages, { role: 'user', content: trimmed } ]);  // Appends
```

### Solution
Changed the message setting to append instead of overwrite:
- Before: `chat.setMessages([ { role: 'user', content: trimmed } ])`
- After: `chat.setMessages([...chat.messages, { role: 'user', content: trimmed } ])`

This preserves the conversation history instead of resetting the messages array on each submit.

## Problem 2: State Closure Issues in Async Operations

### Description
When using `chatStore.messages` in expressions like:
```javascript
[...chatStore.messages, { role: 'assistant', content: result }]
```

The captured `chatStore.messages` was stale (from when the closure was created), not the current state during async tool processing.

### Root Cause
In React functional components, the hook values are snapshots from the render cycle where the function was defined. When async operations complete, these closure values may not reflect the latest state.

### Solution
Use the callback form of setState:
- Changed: `[...chatStore.messages, assistant]`
- To: `chatStore.setMessages((prev) => [...prev, assistant])`

This ensures `prev` is the most current state at the time of the update.

## Problem 3: User Message Disappearing During Tool Calls (Ice Cream Example)

### Description
During image generation tool calls, the user message vanishes when the image and caption are displayed. The LLM response contains both caption text and a tool call, but only the tool call was processed - the caption text was not added to the chat as an assistant message.

### Root Cause
The code only handled captionText addition for `phone_url` tool calls, not for `image_request`:
```javascript
if (captionText) {
  flushSync(() => chatStore.setMessages((prev) => [...prev, { role: 'assistant', content: captionText }]));
}
```
This was inside the phone_url conditional, not applied to image_request.

### Solution
Move the captionText handling outside the specific tool conditionals, or replicate it for image_request. The tool call processing should preserve any text content before or after the JSON structure.

## Problem 4: User Message Disappearing During Image Generation (Callback Form Issue)

### Description
2025-09-06: Image generation tool calls were causing user messages to disappear. The console showed correct state counts (3 → 4 messages after caption + image addition), but the user message still vanished from the UI despite logs showing it was preserved.

### Root Cause
The `useImageGeneration` hook was using stale state access instead of callback forms:

**Before (Problematic):**
```typescript
// In frontend/src/hooks/useChat.ts, generateImage function
chatStore.setMessages([
  ...chatStore.messages,  // <- STALE STATE ACCESS!
  { role: 'assistant', image_url: result.image_url, content: prompt }
]);
```

**Why this causes issues:**
1. `chatStore.messages` captures a closure snapshot from when the function was created
2. During async image generation, this closure may not include the newly added user message
3. The image generation runs in its own timing context, with different state than expected

### Solution
Change to callback form for thread-safe state access:

**Fixed Version:**
```typescript
// In frontend/src/hooks/useChat.ts, generateImage function
chatStore.setMessages((prev) => [
  ...prev,  // <- Current state via callback
  { role: 'assistant', image_url: result.image_url, content: prompt }
]);
```

**Applied to both functions:**
```typescript
// generateImageFromLastMessage also fixed
chatStore.setMessages((prev) => [
  ...prev,
  { role: 'assistant', image_url: result.image_url, content: '' }
]);
```

### Why This Works
1. **Thread Safety**: Callback form guarantees access to current state
2. **Race Condition Elimination**: No timing issues between async operations
3. **State Consistency**: All pending UI updates are included in the calculation
4. **Future-Proof**: Works regardless of when the async operation completes

### Testing & Verification
- ✅ User message now appears immediately when submitted
- ✅ Image generation preserves all messages
- ✅ Caption text properly handled as separate message
- ✅ No more disappearing user messages in image generation flow

### Prevention
When modifying Zustand state in async operations, always use callback forms:
```typescript
// ❌ Bad - Stale state
store.setState([...store.state, newItem])

// ✅ Good - Current state
store.setState((prev) => [...prev, newItem])
```

This applies to all async operations: image generation, API calls, file processing, etc.

## General Prevention Guidelines
✅ **RESOLVED**: All state-related async issues have been addressed through callback forms and proper state management practices.

- Always use `setMessages((prev) => [...prev, newMessage])` patterns for async operations
- For Zustand stores, prefer callback forms over direct state access in async handlers
- Test with real async scenarios to catch closure issues early
- Consider implementing useEffect with proper dependency arrays to handle prop/state changes

## RAG System Troubleshooting

### Problem: "Dimension mismatch: expected 384, got 768"

### Description
When switching between RAG embedding providers (Ollama vs Gemini), you encounter dimension mismatch errors:
```
Dimension mismatch: expected 384, got 768
✅ Query embedding generated successfully
❌ Error in hybrid search: cannot import name 'joinedload'
```

### Root Cause
The database contains embeddings generated from a previous provider, but the current configuration expects a different vector dimension:
- **Ollama**: Typically 384 dimensions (nomic-embed-text)
- **Gemini**: 768 dimensions (text-embedding-004)

The system tries to compare vectors of different sizes, causing cosine similarity calculations to fail.

### Solution
This has been resolved with automatic backward compatibility:
1. **Provider automatically detects dimension mismatches**
2. **System tries to match embedding dimensions with query dimensions**
3. **Graceful fallback to keyword-only search if complete mismatch**
4. **Detailed logging shows dimension compatibility status**

### Prevention
- **Switch providers through the UI** - avoids mid-search dimension conflicts
- **Clear old embeddings** if switching providers: Truncate lore_entries embedding fields
- **Monitor dimensions** in logs during provider changes

### Example Fix Commands
```bash
# Reset embeddings to force regeneration with current provider
python -c "
from backend.database import SessionLocal
from backend.models import LoreEntry

db = SessionLocal()
try:
    db.query(LoreEntry).update({'embedding': None, 'embedding_dimensions': None})
    db.commit()
    print('Embeddings cleared - will regenerate with current provider')
finally:
    db.close()
"
```