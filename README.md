# coolChat

A completely AI-built LLM client inspired by SillyTavern, implemented in Python with a modern React frontend.

## Features

### Core Chat System
- **LLM Integration**: Supports OpenAI, Gemini, and other providers
- **Character Cards**: Import/export JSON and PNG-embedded metadata
- **Advanced Tool Calling**: Phone URL display, image generation, and lore suggestions
- **Persistent Conversations**: SQLite-backed chat history and session management
- **Plugin System**: Extensible with animated backgrounds and tool integrations

### Lorebook System with RAG Integration
- **Structured Knowledge Base**: World information and context injection
- **RAG Hybrid Search**: Semantic similarity + keyword matching with configurable weights
- **Multi-Provider Support**: Ollama, Gemini, OpenAI-compatible embedding providers
- **Progress Tracking**: Embedding generation and status monitoring
- **Modal Editor**: Full-viewport editing interface (UI improvements needed)
- **JSON Field Support**: Keywords with spaces and multiple formats

### Development Status
- ✅ Tool calling system working reliably (phone_url, image_request, lore_suggestions)
- ✅ Database migration to SQLite backend
- ✅ Character import/export functionality (JSON, PNG metadata)
- ✅ Advanced chat interface with swipe navigation and tool integration
- ✅ Theming system with presets and export/import
- ✅ API integrations (Dezgo with JSON config, Pollinations)
- ✅ Extensions support (animatedBackgrounds plugin)
- ✅ Debug system with runtime configuration
- ✅ Test suites (backend: chat, characters, lore, memory)
- ✅ RAG hybrid search with multi-provider embedding support
- 🔶 Lorebook system (backend with RAG complete, UI needs completion with keyword fixes and search improvements)
- ✅ **Circuit Editor Implementation**: Complete ReactFlow-based visual workflow editor with drag-and-drop block creation, color-coded connectors, dynamic block sizing, and full CRUD circuit management
- ~~🔲 Multi-chat and group bot support~~ → **DE-PRIORITIZED**
- ~~🔲 Streaming LLM responses and WebSocket features~~ → **DE-PRIORITIZED**
- 🔆 Circuit Logic Engine: Backend processing and block execution logic (next phase development)

## Architecture
- **Backend**: Python FastAPI with SQLite database
- **Frontend**: React with TypeScript and Zustand state management
- **Tools**: Integrated LLM tools for enhanced interaction
- **Plugins**: Extensible plugin architecture

## Rate Limiting
The lorebook API endpoints are protected by an in-memory sliding-window rate limiter.
Each client IP is limited to 30 requests per minute. Requests exceeding this limit
receive an HTTP `429 Too Many Requests` response. Inactive clients are pruned
automatically to keep memory usage minimal.

## Getting Started
1. Install backend dependencies: `pip install -r backend/requirements.txt`
2. Install frontend dependencies: `cd frontend && npm install`
3. Start backend: `cd backend && python main.py`
4. Start frontend: `cd frontend && npm run dev`

### API Base URL

The frontend reads an optional `VITE_API_BASE` environment variable to determine the
base URL for API requests. During development it defaults to the same origin (handled
by the Vite proxy). For production builds, set this variable to your backend URL:

```bash
VITE_API_BASE=https://api.example.com npm run build
```

## Next Steps & Priority Tasks
1. ✅ **Circuit Editor UI Complete** - Visual workflow editor fully implemented with professional drag-and-drop interface
2. ⏳ **Implement Circuit Logic Engine** - Develop backend processing for circuit execution, block logic, and data flow
3. ⏳ **Block Processing Logic** - Implement actual processing functionality for Logic, Content, Flow, and Integration blocks
4. ⏳ **Prompt Integration** - Connect circuits to the chat system's prompt building pipeline
5. **Enhance lorebook UI** - Complete keywords field fixes and search improvements
6. **Enhance plugin ecosystem** - Plugin manager UI, hot-reload, sandboxing
7. **Optimize performance** - Context management strategies, caching, async improvements
8. **Add comprehensive testing** - Frontend tests, end-to-end flows, performance benchmarks

## Documentation
- [Product Requirements](./coolChatPRD.md)
- [Development Roadmap](./Roadmap.md)
- [Task Tracking](./RooTasks.md)
