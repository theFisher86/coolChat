# CoolChat Project Roadmap

This document outlines recommended features, changes, and improvements for the CoolChat project, based on a review of its current codebase, technical capabilities, and limitations.

## 1. Architectural Enhancements

### 1.1 Database Integration ✅ (COMPLETED)
**Problem:** Current in-memory storage for characters, lore, and memory, backed by JSON files, limits scalability, data integrity, and advanced querying.
**Solution Implemented:** Migrated to SQLite backend with proper schema, async operations, and data persistence.
*   ✅ **Phase 1 (Short-term):** Implemented SQLite with migration scripts
*   🔄 **Phase 2 (Mid-term):** Eventually explore PostgreSQL for multi-user support (low priority)

### 1.2 Robust Error Handling and Logging 🔄 (IN PROGRESS)
**Problem:** Broad `try-except` blocks and reliance on `print()` statements for debugging.
**Recommendation:** Implement a structured logging framework and more granular error handling.
*   ✅ **Debug system:** Comprehensive logging with debug.json configuration
*   🔶 **Feature:** Integrate structured logging (logging module) - partially implemented
*   🔶 **Improvement:** Replace remaining broad try-except blocks with specific exceptions
*   🔲 **Improvement:** Centralized frontend error reporting to backend

### 1.3 Real-time Communication → **DE-PRIORITIZED**
**Note:** Streaming responses and real-time features temporarily de-prioritized after prompt manager implementation.*

## ~~2. Core Feature Development~~ ✅ **COMPLETED**

### 2.1 Advanced Character Management
**Problem:** Character fields are extensive but could benefit from more structured input and AI assistance.
**Recommendation:** Enhance character creation and editing with more intelligent suggestions and validation.
*   **Feature:** AI-powered suggestions for character traits, backstories, and dialogue examples beyond simple field suggestions.
*   **Improvement:** Implement richer text editing for character descriptions and messages (e.g., Markdown support).
*   **Feature:** Versioning for character cards, allowing users to revert to previous states.

### 2.2 Enhanced Lorebook Functionality
**Problem:** Lorebook entry management exists but core functionality needs completion.
**Recommendation:** Complete core lorebook functionality before adding advanced features.
*   **Issue:** Lorebook keywords with spaces and commas support needs implementation.
*   **Issue:** Search functionality returning 422 errors needs to be fixed.
*   **Issue:** UI editor modal and form layout needs completion.
*   **Feature:** Hierarchical lorebooks or nested entries for better organization of complex world information (Future).
*   **Feature:** Visual graph representation of lore connections (e.g., using D3.js or similar libraries in the frontend) (Future).
*   **Improvement:** Advanced search and filtering for lore entries (Future).

### 2.3 Improved Memory System
**Problem:** Memory entries are summarized, but their utilization in chat context could be more dynamic.
**Recommendation:** Develop more intelligent memory retrieval and integration.
*   **Feature:** Context-aware memory retrieval, where the LLM can dynamically pull relevant memories based on the current conversation.
*   **Feature:** User-editable memory summaries and manual tagging for better organization.

### 2.4 Multi-modal Capabilities
**Problem:** Image generation is integrated, but other modalities are not.
**Recommendation:** Explore integration of other AI modalities.
*   **Feature:** Text-to-speech for character voices.
*   **Feature:** Speech-to-text for voice input.
*   **Feature:** Video generation (e.g., short animated clips based on chat).

## ~~3. User Experience & Interface (UI/UX)~~ → **DE-PRIORITIZED**
*Note: Standard UI/UX improvements remain secondary after prompt manager implementation.*

## 3. Prompt Manager & Circuits System
### 3.1 New "Prompt Manager" concept
- Introduction: A flowchart-based UI for managing all prompts, variables, and logic blocks in a visual editor.
--circuits: Drag-and-drop interface allowing users to create complex prompt workflows with if/then/else blocks, random choice blocks, OR/XOR/NOR blocks, random number blocks, random choice from list blocks, counter blocks, variable blocks (from Settings->Prompts->Variables), general prompts, system prompts, placeholders, and ANY other prompt or content sent to the AI.
- Integration: Circuits will replace hardcoded prompt construction, allowing full user customization of AI interactions.

### 3.2 Enhanced Testing & Validation Focus
- Shift primary focus to comprehensive testing and validation of lorebooks and prompt injection systems.
- Ensure all prompt, variable, and text strings identified in the catalog below function correctly within circuits.

### 3.3 System Prompt Extension
- Add user-editable fields for previously non-editable text sent to AI:
  - **Persona Format**: Template for user persona inclusion (e.g., "User Persona: {name}\n{description}")
  - **Tool Descriptions Format**: Descriptive text for tool capabilities
  - **Lore Injection Format**: Format for injecting lore entries (e.g., "[{keyword}] {content}")
  - **Active Lore Title**: Title for active/global lore sections

## 3. User Experience & Interface (UI/UX)

### 3.1 Modern UI/UX Refresh
**Problem:** The current UI is functional but could benefit from a more modern and polished design.
**Recommendation:** Conduct a comprehensive UI/UX review and implement improvements.
*   **Improvement:** Redesign key components for better aesthetics and usability.
*   **Improvement:** Implement more consistent loading indicators, success messages, and error notifications.
*   **Improvement:** Enhance animations and transitions for a smoother feel.

### 3.2 Responsive Design and Accessibility
**Problem:** No explicit responsive design or accessibility considerations.
**Recommendation:** Ensure the application is usable across various devices and for users with disabilities.
*   **Improvement:** Implement responsive design principles for optimal viewing on desktop, tablet, and mobile.
*   **Improvement:** Adhere to WCAG guidelines for accessibility (e.g., keyboard navigation, ARIA attributes, color contrast).

### 3.3 Frontend State Management
**Problem:** Direct API calls and `useState` for complex state might become unwieldy.
**Recommendation:** Introduce a more robust state management solution.
*   **Improvement:** Implement a centralized state management library (e.g., Zustand, React Context with `useReducer`) to manage global application state more effectively.
*   **Improvement:** Refactor API calls into dedicated service modules or custom React hooks.

### 3.4 ~~Theming and Customization~~ ✅ **COMPLETED**
**Problem:** Theming is present but could be more flexible.
**Recommendation:** Expand theming options and user customization.
*   **Feature:** ✅ Allow users to create, save, and share custom themes more easily.
*   **Feature:** ✅ More granular control over UI elements' colors and styles with visual theme preview.
*   **Feature:** Preset theme buttons (Default, Dark, Light, Forest, Ocean, Rose) for quick application.
*   **Feature:** Background color inversion and enhanced animation management.
*   **Feature:** Improved export functionality for custom themes.

## 4. Development & Operations (DevOps)

### 4.1 Comprehensive Testing
**Problem:** Limited frontend tests and no end-to-end tests.
**Recommendation:** Expand test coverage across the entire application.
*   **Improvement:** Implement comprehensive unit and integration tests for all frontend components using `@testing-library/react` and Vitest.
*   **Feature:** Introduce end-to-end tests (e.g., Playwright, Cypress) to validate critical user flows.
*   **Improvement:** Enhance backend test coverage for new features and edge cases.

### 4.2 CI/CD Pipeline
**Problem:** No automated build or deployment process.
**Recommendation:** Set up a Continuous Integration/Continuous Deployment pipeline.
*   **Feature:** Implement CI/CD using GitHub Actions, GitLab CI, or similar tools for automated testing, building, and deployment.
*   **Improvement:** Automate dependency scanning and security checks.

## 5. Extension System Enhancements

### 5.1 Richer Extension API
**Problem:** The current extension system is basic, primarily for client-side JavaScript.
**Recommendation:** Expand the extension API to allow for more powerful integrations.
*   **Feature:** Define a clear and documented API for extensions to interact with backend services (e.g., character data, chat history, LLM calls).
*   **Feature:** Allow extensions to register new UI components or modify existing ones.
*   **Feature:** Implement a secure sandboxing mechanism for extensions to mitigate security risks.

### 5.2 Extension Discovery and Management
**Problem:** Manual loading of extensions.
**Recommendation:** Create a more user-friendly system for discovering, installing, and managing extensions.
*   **Feature:** An in-app "Extension Store" or catalog.
*   **Feature:** One-click installation and uninstallation of extensions.
*   **Feature:** Automatic updates for extensions.

## 6. Strategic Considerations
### 6.1 RAG Implementation Timing
**Consideration:** While RAG (Retrieval-Augmented Generation) remains valuable for performance improvements, evaluate whether it should precede prompt manager work. Key factors:
- Prompt manager/circuits will require extensive testing of current prompt injection systems first.
- RAG may conflict with or duplicate prompt manager functionality.
- Prioritize prompt manager as the foundation for all AI interactions, then assess RAG integration needs.

## Appendix: Comprehensive Prompts & Variables Catalog

### RAG Integration Details
- **Hybrid Search**: Combines semantic similarity (embeddings) with keyword matching
- **Multi-Provider Support**:
  - Ollama (local models, 384 dimensions)
  - Gemini (Google API, 768 dimensions)
  - OpenAI-compatible endpoints
- **Configurable Weights**: Semantic (default 0.4) + Keyword (default 0.6) weight adjustment
- **Embedding Management**: Automatic generation, batch processing, and dimension validation
- **Search API**: `GET /lorebooks/search?q=query&use_rag=true` for RAG-enabled searches
- **Stats Endpoint**: `GET /rag/stats` for dashboard statistics and system status

### A. Chat Messages
- **User Input**: Direct user messages sent as `{"role": "user", "content": user_input}`
- **AI Responses**: Assistant replies as `{"role": "assistant", "content": ai_response}`
- **System Prompts**: Constructed from character and global settings as `{"role": "system", "content": built_system_prompt}`

### B. Character Prompts
- `system_prompt`: Core system instructions
- `personality`: Character personality description
- `scenario`: Scene/context description
- `first_message`: Initial greeting
- `alternate_greetings`: Alternative opening messages
- `mes_example`: Message examples
- `post_history_instructions`: Instructions for history processing

### C. Lorebook Content
- `keywords`: Primary and secondary keywords for trigger detection
- `content`: Lore text injected into context
- `title`: Optional content title
- `embedding`: Base64-encoded vector representation for semantic search
- `embedding_provider`: Source of embedding (ollama, gemini, openai)
- `embedding_dimensions`: Vector size for compatibility checking

### D. System Prompts (Editable via Settings->Prompts)
- `main`: Main system prompt template
- `tool_call`: Instructions for tool usage
- `lore_suggest`: Prompt for suggesting new lore
- `image_summary`: Scene summary for image generation
- **NEW: `persona_format`**: Template for user persona inclusion
- **NEW: `tool_descriptions_format`**: Descriptive text for tools
- **NEW: `lore_injection_format`**: Format for lore entry injection
- **NEW: `active_lore_title`**: Title for active lore sections

### E. Variables (Editable)
- Custom key-value pairs from prompts.json `"variables"` object
- Replaced as `{{key}}` in prompts before AI submission

### F. Tool Messages
- `image_request`: `{"type": "image_request", "payload": {"prompt": "..."}}`
- `phone_url`: `{"type": "phone_url", "payload": {"url": "..."}}`
- `lore_suggestions`: `{"type": "lore_suggestions", "payload": {"items": [{"keyword": "...", "content": "..."}]}}`

### G. Image Prompts
- Explicit prompts sent to image APIs as query strings or form data (e.g., "detailed image description")

This catalog serves as the source of truth for refining the prompt manager scope and ensuring all AI text interactions are manageable within circuits.

## 7. RAG API Documentation

### RAG Statistics Endpoint
```http
GET /rag/stats
```
**Response Schema:**
```json
{
  "total_entries": 125,
  "embedded_entries": 95,
  "embedding_percentage": 76.0,
  "last_embedding_date": "2025-01-09T14:30:25Z",
  "provider_type": "ollama",
  "provider_status": "Ready",
  "api_key_configured": true
}
```

**Fields:**
- `total_entries`: Total number of lore entries in database
- `embedded_entries`: Number of entries with vector embeddings
- `embedding_percentage`: Percentage of entries with embeddings (0.1 precision)
- `last_embedding_date`: ISO timestamp of most recent embedding update
- `provider_type`: Current embedding provider (ollama, gemini, openai)
- `provider_status`: "Ready" or "Requires API Key"
- `api_key_configured`: Boolean indicating if provider is properly configured

### Lorebook Search with RAG
```http
GET /lorebooks/search?q=query&limit=10&use_rag=true
```
**Query Parameters:**
- `q`: Search query (required)
- `limit`: Maximum results (default: 10)
- `use_rag`: Enable RAG hybrid search (default: false)

**RAG Response Format (when use_rag=true):**
```json
[
  {
    "id": 42,
    "title": "Dark Forest Village",
    "content": "The forest village is surrounded by ancient oaks...",
    "lorebook_name": "Fantasy World",
    "lorebook_id": 2,
    "keywords": ["village", "forest", "elves"],
    "secondary_keywords": ["settlement"],
    "logic": "AND ANY",
    "trigger": 100.0,
    "order": 0.0,
    "score": 0.85,
    "keyword_score": 15.2,
    "semantic_score": 0.73,
    "matched_terms": ["forest", "village"]
  }
]
```

### RAG Configuration
Database-configured settings in `rag_config` table:
- `provider`: Embedding provider (ollama/ollama, gemini, openai)
- `ollama_base_url`: Ollama server address (default: localhost:11434)
- `ollama_model`: Ollama model name (default: nomic-embed-text:latest)
- `gemini_api_key`: API key for Gemini provider
- `gemini_model`: Gemini model (default: text-embedding-004)
- `top_k_candidates`: Keyword candidates for reranking (default: 200)
- `keyword_weight`: Weight for exact matches (default: 0.6)
- `semantic_weight`: Weight for similarity (default: 0.4)
- `similarity_threshold`: Minimum similarity for matches (default: 0.5)
- `batch_size`: Embedding generation batch size (default: 32)
- `embedding_dimensions`: Expected vector dimensions (384 for Ollama, 768 for Gemini)

This roadmap provides a strategic direction for the CoolChat project, focusing on improving its core architecture, expanding features, enhancing user experience, streamlining development, and empowering its extension ecosystem. The phased approach allows for incremental development and continuous improvement.