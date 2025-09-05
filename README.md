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
- ✅ Tool calling system working reliably
- ✅ Database migration to SQLite backend
- ✅ Character import/export functionality
- 🔶 Lorebook system (backend complete, UI needs completion)
- 🔲 Multi-chat and group bot support
- 🔲 Video/image modalities

## Architecture
- **Backend**: Python FastAPI with SQLite database
- **Frontend**: React with TypeScript and Zustand state management
- **Tools**: Integrated LLM tools for enhanced interaction
- **Plugins**: Extensible plugin architecture

## Getting Started
1. Install dependencies: `pip install -r backend/requirements.txt`
2. Start backend: `cd backend && python main.py`
3. Start frontend: `cd frontend && npm install && npm run dev`

## Documentation
- [Product Requirements](./coolChatPRD.md)
- [Development Roadmap](./Roadmap.md)
- [Task Tracking](./RooTasks.md)
