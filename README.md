# coolChat

A completely AI-built LLM client inspired by SillyTavern, implemented in Python with a modern React frontend.

## Features

### Core Chat System
- **LLM Integration**: Supports OpenAI, Gemini, and other providers
- **Character Cards**: Import/export JSON and PNG-embedded metadata
- **Advanced Tool Calling**: Phone URL display, image generation, and lore suggestions
- **Persistent Conversations**: SQLite-backed chat history and session management
- **Plugin System**: Extensible with animated backgrounds and tool integrations

### Lorebook System (In Development)
- **Structured Knowledge Base**: World information and context injection
- **Advanced Search**: Semantic keyword matching with scoring
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
- 🔶 Lorebook system (backend complete, UI needs completion with keyword fixes and search improvements)
- ~~🔲 Multi-chat and group bot support~~ → **DE-PRIORITIZED**
- ~~🔲 Streaming LLM responses and WebSocket features~~ → **DE-PRIORITIZED**
- 🔲 Advanced RAG/vector search integration
- 🔆 Prompt Manager & Circuits System (new priority): Flowchart-based UI for comprehensive prompt management with logic blocks, variables, and visual workflow design

## Architecture
- **Backend**: Python FastAPI with SQLite database
- **Frontend**: React with TypeScript and Zustand state management
- **Tools**: Integrated LLM tools for enhanced interaction
- **Plugins**: Extensible plugin architecture

## Getting Started
1. Install backend dependencies: `pip install -r backend/requirements.txt`
2. Install frontend dependencies: `cd frontend && npm install`
3. Start backend: `cd backend && python main.py`
4. Start frontend: `cd frontend && npm run dev`

## Next Steps & Priority Tasks
1. **Implement Prompt Manager & Circuits System** - Develop visual flowchart UI for managing all prompts, variables, and logic blocks with if/then/else, random choices, counters, etc.
2. **Enhance System Prompt Editing** - Add user-editable fields for previously hardcoded text sent to AI (persona format, tool descriptions, lore injection format)
3. **Comprehensive Testing of Prompt Injection** - Ensure lorebooks, character fields, variables, and all editable prompts function correctly within circuits
4. ~~Implement multi-chat support~~ **DE-PRIORITIZED**
5. ~~Add streaming responses~~ **DE-PRIORITIZED**
6. **Enhance plugin ecosystem** - Plugin manager UI, hot-reload, sandboxing
7. **Optimize performance** - Context management strategies, caching, async improvements
8. **Add comprehensive testing** - Frontend tests, end-to-end flows, performance benchmarks

## Documentation
- [Product Requirements](./coolChatPRD.md)
- [Development Roadmap](./Roadmap.md)
- [Task Tracking](./RooTasks.md)
