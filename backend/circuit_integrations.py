"""Integration adapters for circuits.

This module provides adapters for connecting circuits with existing systems:
- Chat endpoints (LLM providers)
- Lore injection (RAG service)
- Character data
"""

import json
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
import httpx
from .database import SessionLocal
from .models import Character, ChatSession, ChatMessage, LoreEntry
from .config import load_config, Provider
from .rag_service import get_rag_service


class CircuitIntegrationAdapter:
    """Main integration adapter for circuits."""

    def __init__(
        self,
        db: Optional[Session] = None,
        rag_service: Optional[Any] = None
    ):
        self.db = db or SessionLocal()
        self.rag_service = rag_service or get_rag_service(db=self.db)

    def call_llm(
        self,
        provider: str,
        model: str,
        prompt: str,
        character_id: Optional[int] = None,
        temperature: float = 0.7
    ) -> str:
        """Call an LLM with the given prompt."""
        cfg = load_config()

        if provider == Provider.ECHO.value:
            return f"Echo: {prompt[:100]}..."

        provider_config = cfg.providers.get(Provider(provider), cfg.providers.get(Provider.OPENAI, None))
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider}")

        if not provider_config.api_key:
            raise ValueError(f"No API key configured for provider: {provider}")

        # Build system prompt from character if provided
        system_msg = None
        if character_id:
            char = self.db.get(Character, character_id)
            if char and char.system_prompt:
                system_msg = f"Character: {char.name}\n{char.system_prompt}"

        # Call LLM using existing implementation
        return self._call_llm_api(
            Provider(provider),
            provider_config,
            model,
            prompt,
            system_msg,
            temperature
        )

    async def call_llm_async(
        self,
        provider: str,
        model: str,
        prompt: str,
        character_id: Optional[int] = None,
        temperature: float = 0.7
    ) -> str:
        """Async version of call_llm."""
        import asyncio
        loop = asyncio.get_running_loop()

        # Run sync version in thread pool
        result = await loop.run_in_executor(
            None,
            lambda: self.call_llm(provider, model, prompt, character_id, temperature)
        )

        return result

    def _call_llm_api(
        self,
        provider: Provider,
        pcfg,
        model: str,
        prompt: str,
        system_msg: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Low-level LLM API call."""
        base_url = getattr(pcfg, 'api_base', None)
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})

        if provider == Provider.OPENAI:
            if not base_url:
                base_url = "https://api.openai.com/v1"
            return self._call_openai_api(base_url, pcfg.api_key, model, messages, temperature, timeout)

        elif provider == Provider.GEMINI:
            if not base_url:
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            return self._call_openai_api(base_url, pcfg.api_key, model, messages, temperature, timeout)

        elif provider == Provider.OPENROUTER:
            base_url = "https://openrouter.ai/api/v1"
            return self._call_openai_api(base_url, pcfg.api_key, model, messages, temperature, timeout)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _call_openai_api(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict],
        temperature: float,
        timeout
    ) -> str:
        """Call OpenAI-compatible API."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{base_url}/chat/completions", headers=headers, json=body)

            if resp.status_code >= 400:
                raise ValueError(f"LLM API error {resp.status_code}: {resp.text}")

            data = resp.json()
            return data['choices'][0]['message']['content'].strip()

    def query_lore(self, keywords: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Query lore entries by keywords."""
        if not keywords:
            return []

        # Use RAG service for semantic search
        query = " ".join(keywords)
        candidates = self.rag_service.search(query, top_k=limit)

        # Format results
        results = []
        for candidate in candidates:
            # Get full entry from database
            entry = self.db.query(LoreEntry).get(candidate['id'])
            if entry:
                results.append({
                    'id': entry.id,
                    'keyword': keywords[0] if keywords else entry.keywords[0] if entry.keywords else '',
                    'content': entry.content,
                    'score': candidate['score']
                })

        return results[:limit]

    def get_character_context(self, character_id: int) -> Dict[str, Any]:
        """Get character context data."""
        char = self.db.get(Character, character_id)
        if not char:
            return {}

        return {
            'name': char.name,
            'description': char.description,
            'personality': char.personality,
            'scenario': char.scenario,
            'system_prompt': char.system_prompt
        }

    def get_recent_chat_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat messages for context."""
        recent_messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.chat_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        # Reverse to get chronological order
        messages = []
        for msg in reversed(recent_messages):
            messages.append({
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat()
            })

        return messages

    def build_prompt_with_context(
        self,
        base_prompt: str,
        character_id: Optional[int] = None,
        lore_keywords: Optional[List[str]] = None,
        chat_session_id: Optional[str] = None
    ) -> str:
        """Build a complete prompt with various context sources."""
        prompt_parts = []

        # Add character context
        if character_id:
            char_context = self.get_character_context(character_id)
            if char_context.get('system_prompt'):
                prompt_parts.append(f"System: {char_context['system_prompt']}")

        # Add lore entries
        if lore_keywords:
            lore_entries = self.query_lore(lore_keywords)
            if lore_entries:
                lore_text = "\n".join([
                    f"[{entry['keyword']}]: {entry['content']}"
                    for entry in lore_entries
                ])
                prompt_parts.append(f"World Information:\n{lore_text}")

        # Add chat history
        if chat_session_id:
            chat_history = self.get_recent_chat_history(chat_session_id, 5)
            if chat_history:
                history_text = "\n".join([
                    f"{msg['role'].title()}: {msg['content']}"
                    for msg in chat_history
                ])
                prompt_parts.append(f"Conversation History:\n{history_text}")

        # Add base prompt
        prompt_parts.append(f"Query: {base_prompt}")

        return "\n\n".join(prompt_parts)


def get_llm_connector(
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Create LLM connector configuration for circuits."""
    return {
        'type': 'llm_connector',
        'provider': provider,
        'model': model,
        'api_key': api_key,
        'temperature': 0.7
    }


def get_prompt_builder(
    template: str,
    variables: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create prompt builder configuration."""
    return {
        'type': 'prompt_builder',
        'template': template,
        'variables': variables or {}
    }


def get_lore_injector(
    keywords: List[str],
    limit: int = 5
) -> Dict[str, Any]:
    """Create lore injection configuration."""
    return {
        'type': 'lore_injection',
        'keywords': keywords,
        'limit': limit
    }


def get_variable_processor(
    operation: str,
    variable_name: str,
    value: Any = ""
) -> Dict[str, Any]:
    """Create variable processor configuration."""
    return {
        'type': 'variable_processor',
        'operation': operation,
        'variable_name': variable_name,
        'value': value
    }


def get_conditional_node(
    condition: str
) -> Dict[str, Any]:
    """Create conditional node configuration."""
    return {
        'type': 'conditional',
        'condition': condition
    }