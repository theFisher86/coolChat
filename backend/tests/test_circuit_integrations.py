"""Unit tests for circuit_integrations.py - Integration adapters for circuits."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
import httpx
from datetime import datetime

from backend.circuit_integrations import (
    CircuitIntegrationAdapter,
    get_llm_connector,
    get_prompt_builder,
    get_lore_injector,
    get_variable_processor,
    get_conditional_node,
)
from backend.models import Character, LoreEntry, ChatSession, ChatMessage
from backend.config import Provider


class TestCircuitIntegrationAdapter:
    """Tests for CircuitIntegrationAdapter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.adapter = CircuitIntegrationAdapter(db=self.mock_db)

    def test_init_with_db(self):
        """Test initialization with database session."""
        mock_db = Mock(spec=Session)
        adapter = CircuitIntegrationAdapter(db=mock_db)

        assert adapter.db == mock_db
        assert adapter.rag_service is not None

    @patch('backend.circuit_integrations.load_config')
    def test_call_llm_echo_provider(self, mock_config):
        """Test calling LLM with echo provider."""
        mock_pcfg = Mock()
        mock_pcfg.providers = {}
        mock_config.return_value = mock_pcfg

        result = self.adapter.call_llm("echo", "test-model", "Test prompt")

        assert result == "Echo: Test prompt:1..."

    @patch('backend.circuit_integrations.load_config')
    def test_call_llm_openai_provider(self, mock_config):
        """Test calling LLM with OpenAI provider."""
        mock_pcfg = Mock()
        mock_pcfg.api_key = "test-key-123"
        mock_cfg = Mock()
        mock_cfg.providers = {Provider.OPENAI: mock_pcfg}
        mock_config.return_value = mock_cfg

        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Test response'}}]
            }
            mock_client.return_value.__enter__.return_value = mock_response

            result = self.adapter.call_llm("openai", "gpt-4", "Test prompt", temperature=0.7)

            assert result == "Test response"
            mock_client.assert_called_once()
            call_args = mock_client.call_args[0][0].post.call_args
            assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
            headers = call_args[1]['headers']
            assert "Bearer test-key-123" in headers['Authorization']

    @patch('backend.circuit_integrations.load_config')
    def test_call_llm_missing_api_key(self, mock_config):
        """Test calling LLM with missing API key."""
        mock_pcfg = Mock()
        mock_pcfg.api_key = None
        mock_cfg = Mock()
        mock_cfg.providers = {Provider.OPENAI: mock_pcfg}
        mock_config.return_value = mock_cfg

        with pytest.raises(ValueError, match="No API key configured"):
            self.adapter.call_llm("openai", "gpt-4", "Test prompt")

    @patch('backend.circuit_integrations.load_config')
    def test_call_llm_unknown_provider(self, mock_config):
        """Test calling LLM with unknown provider."""
        mock_pcfg = Mock()
        mock_pcfg.providers = {}
        mock_config.return_value = mock_pcfg

        with pytest.raises(ValueError, match="Unknown provider"):
            self.adapter.call_llm("unknown", "gpt-4", "Test prompt")

    @patch('backend.circuit_integrations.load_config')
    def test_call_llm_with_character(self, mock_config):
        """Test calling LLM with character context."""
        mock_pcfg = Mock()
        mock_pcfg.api_key = "test-key"
        mock_cfg = Mock()
        mock_cfg.providers = {Provider.OPENAI: mock_pcfg}
        mock_config.return_value = mock_cfg

        # Mock character
        mock_char = Mock()
        mock_char.system_prompt = "You are a helpful assistant."
        mock_char.name = "TestChar"
        self.adapter.db.get.return_value = mock_char

        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Character response'}}]
            }
            mock_client.return_value.__enter__.return_value = mock_response

            result = self.adapter.call_llm("openai", "gpt-4", "Test prompt", character_id=1)

            assert result == "Character response"

            # Check that character system prompt was included in messages
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            messages = call_args[1]['json']['messages']
            assert len(messages) == 2
            assert messages[0]['role'] == 'system'
            assert "Character: TestChar" in messages[0]['content']
            assert "You are a helpful assistant." in messages[0]['content']

    @patch('backend.circuit_integrations.load_config')
    def test_call_llm_async(self, mock_config):
        """Test async call to LLM."""
        mock_pcfg = Mock()
        mock_pcfg.api_key = "test-key"
        mock_cfg = Mock()
        mock_cfg.providers = {Provider.OPENAI: mock_pcfg}
        mock_config.return_value = mock_cfg

        async def async_test():
            import asyncio

            with patch.object(self.adapter, 'call_llm', return_value="Async response") as mock_call:
                result = await self.adapter.call_llm_async("openai", "gpt-4", "Test prompt")
                assert result == "Async response"
                mock_call.assert_called_once_with("openai", "gpt-4", "Test prompt", None, 0.7)

        import asyncio
        asyncio.run(async_test())

    @patch('httpx.Client')
    @patch('backend.circuit_integrations.load_config')
    def test_call_openai_api_error(self, mock_config, mock_client_class):
        """Test handling of OpenAI API errors."""
        mock_pcfg = Mock()
        mock_pcfg.api_key = "test-key"
        mock_cfg = Mock()
        mock_cfg.providers = {Provider.OPENAI: mock_pcfg, Provider.ECHO: None}
        mock_config.return_value = mock_cfg

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=None, response=mock_response)

        mock_client = Mock()
        mock_client.post.side_effect = httpx.HTTPStatusError("Bad Request", request=None, response=mock_response)
        mock_client_class.return_value.__enter__.return_value = mock_client

        with pytest.raises(ValueError, match="LLM API error 400"):
            self.adapter._call_llm_api(Provider.OPENAI, mock_pcfg, "gpt-4", "Test prompt")

    def test_query_lore_no_keywords(self):
        """Test querying lore with no keywords."""
        result = self.adapter.query_lore([])
        assert result == []

    def test_query_lore_with_keywords(self, mocker):
        """Test querying lore with keywords."""
        mock_candidates = [
            {'id': 1, 'score': 0.9},
            {'id': 2, 'score': 0.8}
        ]

        mock_lore1 = Mock(spec=LoreEntry)
        mock_lore1.id = 1
        mock_lore1.content = "Lore content 1"
        mock_lore1.keywords = ["keyword1"]

        mock_lore2 = Mock(spec=LoreEntry)
        mock_lore2.id = 2
        mock_lore2.content = "Lore content 2"
        mock_lore2.keywords = ["keyword2"]

        self.adapter.db.query.return_value.get.side_effect = [mock_lore1, mock_lore2]

        mock_rag_search = mocker.patch.object(self.adapter.rag_service, 'search', return_value=mock_candidates)

        result = self.adapter.query_lore(["keyword1"], limit=5)

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['content'] == "Lore content 1"
        assert result[0]['score'] == 0.9
        assert result[1]['id'] == 2
        assert result[1]['content'] == "Lore content 2"
        assert result[1]['score'] == 0.8

        mock_rag_search.assert_called_once_with("keyword1", top_k=5)

    def test_query_lore_no_results_from_rag(self, mocker):
        """Test querying lore when RAG returns no results."""
        mock_rag_search = mocker.patch.object(self.adapter.rag_service, 'search', return_value=[])

        result = self.adapter.query_lore(["keyword1"], limit=5)

        assert result == []
        mock_rag_search.assert_called_once_with("keyword1", top_k=5)

    def test_get_character_context_found(self):
        """Test getting character context when character exists."""
        mock_char = Mock(spec=Character)
        mock_char.name = "TestCharacter"
        mock_char.description = "Test description"
        mock_char.personality = "Friendly"
        mock_char.scenario = "Test scenario"
        mock_char.system_prompt = "You are a test character."

        self.adapter.db.get.return_value = mock_char

        result = self.adapter.get_character_context(1)

        expected = {
            'name': 'TestCharacter',
            'description': 'Test description',
            'personality': 'Friendly',
            'scenario': 'Test scenario',
            'system_prompt': 'You are a test character.'
        }

        assert result == expected
        self.adapter.db.get.assert_called_once_with(Character, 1)

    def test_get_character_context_not_found(self):
        """Test getting character context when character doesn't exist."""
        self.adapter.db.get.return_value = None

        result = self.adapter.get_character_context(1)

        assert result == {}
        self.adapter.db.get.assert_called_once_with(Character, 1)

    def test_get_recent_chat_history(self):
        """Test getting recent chat history."""
        mock_messages = [
            Mock(spec=ChatMessage),
            Mock(spec=ChatMessage)
        ]

        mock_messages[0].chat_id = "session1"
        mock_messages[0].role = "user"
        mock_messages[0].content = "Hello"
        mock_messages[0].created_at = datetime(2023, 1, 1, 10, 0, 0)

        mock_messages[1].chat_id = "session1"
        mock_messages[1].role = "assistant"
        mock_messages[1].content = "Hi there"
        mock_messages[1].created_at = datetime(2023, 1, 1, 10, 1, 0)

        # Mock query chain
        mock_query = Mock()
        self.adapter.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_messages
        self.adapter.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value[0] = mock_messages[0]
        self.adapter.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value[1] = mock_messages[1]

        result = self.adapter.get_recent_chat_history("session1", 10)

        assert len(result) == 2
        assert result[0]['role'] == 'assistant'  # Should be reversed (chronological)
        assert result[0]['content'] == 'Hi there'
        assert result[1]['role'] == 'user'
        assert result[1]['content'] == 'Hello'

    def test_build_prompt_with_context(self):
        """Test building prompt with various context sources."""
        # Mock character
        mock_char = Mock(spec=Character)
        mock_char.system_prompt = "You are helpful."
        self.adapter.db.get.return_value = mock_char

        # Mock lore results
        mock_lore_results = [
            {'keyword': 'magic', 'content': 'Magic is real'}
        ]
        mock_query_lore = Mock(return_value=mock_lore_results)
        self.adapter.query_lore = mock_query_lore

        # Mock chat history
        mock_chat_history = [
            {'role': 'user', 'content': 'Hello'}
        ]
        mock_get_history = Mock(return_value=mock_chat_history)
        self.adapter.get_recent_chat_history = mock_get_history

        result = self.adapter.build_prompt_with_context(
            "How do I cast a spell?",
            character_id=1,
            lore_keywords=['magic'],
            chat_session_id="session1"
        )

        assert "System: You are helpful." in result
        assert "[magic]: Magic is real" in result
        assert "Conversation History:" in result
        assert "Query: How do I cast a spell?" in result

    def test_build_prompt_minimal(self):
        """Test building prompt with minimal context."""
        result = self.adapter.build_prompt_with_context("Simple question")

        assert result == "\n\nQuery: Simple question"


class TestHelperFunctions:
    """Tests for helper functions in circuit_integrations.py."""

    def test_get_llm_connector(self):
        """Test creating LLM connector configuration."""
        config = get_llm_connector("openai", "gpt-4o-mini", "key123")

        assert config == {
            'type': 'llm_connector',
            'provider': 'openai',
            'model': 'gpt-4o-mini',
            'api_key': 'key123',
            'temperature': 0.7
        }

    def test_get_prompt_builder(self):
        """Test creating prompt builder configuration."""
        config = get_prompt_builder("Hello {{name}}!", {"name": "World"})

        assert config == {
            'type': 'prompt_builder',
            'template': 'Hello {{name}}!',
            'variables': {'name': 'World'}
        }

    def test_get_lore_injector(self):
        """Test creating lore injector configuration."""
        config = get_lore_injector(["magic", "spells"], 5)

        assert config == {
            'type': 'lore_injection',
            'keywords': ['magic', 'spells'],
            'limit': 5
        }

    def test_get_variable_processor(self):
        """Test creating variable processor configuration."""
        config = get_variable_processor("set", "greeting", "Hello World")

        assert config == {
            'type': 'variable_processor',
            'operation': 'set',
            'variable_name': 'greeting',
            'value': 'Hello World'
        }

    def test_get_conditional_node(self):
        """Test creating conditional node configuration."""
        config = get_conditional_node("count > 5")

        assert config == {
            'type': 'conditional',
            'condition': 'count > 5'
        }


class TestIntegrationEdgeCases:
    """Tests for edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = CircuitIntegrationAdapter()

    def test_call_llm_empty_prompt(self, mocker):
        """Test calling LLM with empty prompt."""
        mock_config = Mock()
        mock_config.api_key = "test-key"
        mock_pcfg = Mock()
        mock_pcfg.providers = {}
        mocker.patch('backend.circuit_integrations.load_config', return_value=mock_pcfg)

        # This should use echo provider since no provider is specified
        result = self.adapter.call_llm("echo", "test-model", "")

        assert result == "Echo: :1..."  # Empty prompt becomes single char

    def test_query_lore_empty_keywords_after_join(self, mocker):
        """Test querying lore with keywords that result in empty query."""
        mock_rag_search = mocker.patch.object(self.adapter.rag_service, 'search', return_value=[])

        result = self.adapter.query_lore([])

        # Should short circuit and not call RAG
        mock_rag_search.assert_not_called()
        assert result == []

    def test_get_chat_history_empty_session(self, mocker):
        """Test getting chat history for empty session."""
        mock_query = mocker.patch.object(self.adapter.db, 'query')

        result = self.adapter.get_recent_chat_history("", 10)

        # Should still perform query but may return empty
        assert isinstance(result, list)

    def test_build_prompt_with_none_character_id(self, mocker):
        """Test building prompt when character_id is None."""
        result = self.adapter.build_prompt_with_context("Test", character_id=None)

        assert "System:" not in result  # No character system prompt
        assert "Query: Test" in result