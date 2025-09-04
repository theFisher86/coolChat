# Project Overview

CoolChat is a web application designed to facilitate interactive chat experiences, primarily focused on character-driven conversations. It features a React-based frontend and a FastAPI-based Python backend. The application allows users to define and manage characters, lorebooks (world information), and memories, which are then used to inform conversations with various Large Language Model (LLM) providers. It also includes functionality for AI-powered image generation and dynamic theme suggestions.

The backend aims to mimic a subset of SillyTavern's functionality, particularly for character and lorebook management.  The web app overall is meant to offer all the functionality and features of SillyTavern but in a much more memory efficient package thanks to React and Python.  

The plugins folder allows for additional plugins to be installed which will enhance the feature set with new functionality. The entire UI and webapp should be built with this in mind, ensuring that every aspect of the webapp is easy to extend and modify via plugins.

# Tech Stack

## Frontend
*   **Framework:** React
*   **Build Tool:** Vite
*   **Testing:** Vitest

## Backend
*   **Web Framework:** FastAPI
*   **ASGI Server:** Uvicorn
*   **HTTP Client:** httpx
*   **Testing:** pytest
*   **Data Serialization:** Pydantic
*   **LLM Integrations:** OpenAI, OpenRouter, Google Gemini, Pollinations (via OpenAI-compatible API), ollama, NVIDIA NIM API, NanoGPT, Chutes.ai
*   **Image Generation Integrations:** Pollinations, Dezgo

# Project Structure

```
d:\AlpacaBarn\Tools\coolChat\
├───.git\...
├───.pytest_cache\...
├───.vscode\
├───backend\
│   ├───__init__.py
│   ├───config.py         # Application configuration (LLM providers, debug, user persona, etc.)
│   ├───database.py       # (Not explicitly reviewed, but likely related to data storage)
│   ├───main.py           # Main FastAPI application, defines API endpoints
│   ├───models.py         # Pydantic models for data structures (Character, LoreEntry, MemoryEntry, etc.)
│   ├───requirements.txt  # Python dependencies
│   ├───schemas.py        # (Not explicitly reviewed, but likely Pydantic schemas)
│   ├───storage.py        # Handles JSON file loading/saving for persistence
│   ├───__pycache__\
│   ├───routers\          # API route definitions (e.g., characters, chat)
│   │   ├───characters.py
│   │   └───chat.py
│   └───tests\            # Backend unit and integration tests
├───extensions\           # Frontend extensions (e.g., animatedBackgrounds)
│   └───animatedBackgrounds\
│       ├───client.js
│       └───manifest.json
├───frontend\
│   ├───index.html
│   ├───package-lock.json
│   ├───package.json      # Frontend dependencies and scripts
│   ├───vite.config.js
│   ├───dist\...
│   ├───node_modules\...
│   └───src\
│       ├───api.js        # (Likely handles API calls to backend)
│       ├───App.css
│       ├───App.jsx       # Main React component
│       ├───App.test.jsx
│       ├───main.jsx
│       ├───pluginHost.js
│       └───test.setup.js
├───node_modules\...
├───plugins\              # (Potentially backend plugins, or related to extensions)
│   └───animatedBackgrounds\
├───public\               # Static assets served by backend
│   ├───characters\       # Stored character avatars/data
│   ├───images\
│   ├───lorebooks\        # Stored lorebook data
│   └───templates\
├───.gitignore
├───dezgo_api.html
├───dezgo_info.json
├───LICENSE
├───package-lock.json
└───README.md
```

# Backend Details

The backend is built with FastAPI and provides a RESTful API for managing various aspects of the chat application.

## Key Features:
*   **Character Management:**
    *   CRUD operations for `Character` objects.
    *   Support for importing character data from PNG image metadata (SillyTavern format) and JSON files.
    *   AI-powered suggestions for character fields (e.g., description, personality).
    *   AI-powered avatar generation using external image generation services.
*   **Lorebook Management:**
    *   CRUD operations for `Lorebook` and `LoreEntry` objects.
    *   Lore entries can be associated with keywords and logic for contextual triggering during chat.
*   **Memory Management:**
    *   CRUD operations for `MemoryEntry` objects, which store snippets of conversation or information with auto-generated summaries.
*   **Chat Functionality:**
    *   The `/chat` endpoint is the core of the conversation system.
    *   It dynamically selects an LLM provider (Echo, OpenAI, OpenRouter, Gemini, Pollinations) based on the application configuration.
    *   Constructs a system message for the LLM based on the active character's details, user persona, and relevant lorebook entries (including triggered lore).
    *   Manages chat history per session, with a mechanism to trim history to fit token limits.
*   **Configuration:**
    *   Provides endpoints to retrieve and update application settings, including:
        *   Active LLM provider and its API key/base/model/temperature.
        *   Active character and lorebooks.
        *   Debug logging settings.
        *   User persona details.
        *   Maximum context tokens for LLMs.
        *   Image generation provider (Pollinations, Dezgo) and their settings.
        *   Theme settings.
    *   Configuration is persisted to JSON files using `backend/storage.py`.
*   **Model Listing:**
    *   An endpoint to list available models for configured LLM providers.
*   **Static File Serving:**
    *   Serves character avatars, lorebook data, and other static assets from the `public/` directory.
    *   Serves frontend extensions from the `extensions/` directory.

## Data Persistence
Data for characters, lore, lorebooks, memory, and chat histories are stored in JSON files within the application's data directory (likely managed by `backend/storage.py`).

# Frontend Details

The frontend is a React application built with Vite, providing the user interface for interacting with the CoolChat backend.

## Key Features:
*   **User Interface:** Provides a web-based interface for chat, character management, lorebook management, and configuration.
*   **API Interaction:** Communicates with the FastAPI backend to perform all operations.
*   **Extensible:** Supports frontend extensions, as seen with `extensions/animatedBackgrounds`.

# Roadmap Suggestions

Here are some initial roadmap suggestions based on the on-going project:

## Short-Term (Improvements & Refinements)
1.  **Comprehensive Error Handling & User Feedback:** Enhance error handling in both frontend and backend to provide more user-friendly messages and recovery options. For example, if an LLM API call fails, the user should get a clear explanation, not just a generic HTTP error.
2.  **Improved Chat History Management:** While there's a trimming mechanism, explore more sophisticated history management strategies (e.g., summarization of older turns) to maximize context within token limits.
3.  **Frontend State Management:** Evaluate and potentially introduce a more robust state management solution for the React frontend (e.g., Redux, Zustand, React Context API) to handle complex application state more effectively, especially with character and lorebook data.
4.  **Input Validation on Frontend:** Implement client-side validation for forms (e.g., character creation, config updates) to provide immediate feedback to users and reduce unnecessary backend calls.
5.  **Documentation for Extensions:** Create clear documentation for how to develop and integrate new frontend extensions.
6.  **Refactor `main.py`:** The `main.py` file is quite large. Consider breaking it down into smaller, more manageable modules or using FastAPI's APIRouter to organize endpoints. (Already partially done with `routers/`, but more could be done).
7.  **Mobile UI:** The UI needs to be tweaked to work properly on mobile and other screensizes. The Header bar at the top should be horizontally scrollable in the mobile UI. The mobile UI should focus on maximizing screenspace for reading the chat text.

## Mid-Term (New Features)
1.  **Advanced Lorebook Triggering:** Expand the lorebook triggering logic to support more complex conditions, such as regular expressions, proximity to other keywords, or sentiment analysis.
2.  **Tool/Plugin Marketplace:** Create a system for users to discover, install, and manage backend and frontend plugins/tools directly within the application. This could involve a simple registry or a more elaborate marketplace.
3.  **Image Generation Enhancements:**
    *   **Image-to-Image:** Allow users to upload an image and use it as a base for AI image generation.
    *   **Inpainting/Outpainting:** Integrate features for modifying specific parts of an image or extending its boundaries.
    *   **Multiple Image Providers:** Expand support for more image generation APIs beyond Pollinations and Dezgo.
4.  **Voice Input/Output:** Integrate speech-to-text for voice input and text-to-speech for voice output, enabling a more natural conversational experience.
5.  **Export/Import of All Data:** Provide a comprehensive export/import feature for all user data (characters, lorebooks, memories, chat histories) to allow for backups and migration.

## Long-Term (Vision & Scalability)
1.  **Database Integration:** Migrate from JSON file-based persistence to a proper database (e.g., PostgreSQL, SQLite) for better scalability, data integrity, and query capabilities, especially if multi-user support is implemented.
2.  **Real-time Chat:** Implement WebSockets for real-time chat updates, providing a more responsive and interactive user experience.
3.  **Advanced AI Features:**
    *   **Contextual Memory Retrieval:** Develop more intelligent mechanisms for retrieving relevant memories based on the current conversation context.
    *   **Self-Correction/Reflection:** Implement AI agents that can reflect on past conversations and self-correct their behavior or knowledge.
    *   **Multi-Agent Conversations:** Enable scenarios where multiple AI characters can interact with each other or with the user.
