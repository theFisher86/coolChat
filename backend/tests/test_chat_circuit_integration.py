"""Integration tests for chat system with circuits - end-to-end workflow testing."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone

from backend.main import app
from backend.database import create_tables
from backend.models import Circuit


# Setup database for tests
create_tables()


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


class TestChatCircuitIntegration:
    """Tests for end-to-end chat system with circuits integration."""

    def test_chat_with_simple_circuit(self, client):
        """Test chat message processing with a simple circuit."""
        # Create a simple circuit for chat processing
        circuit_data = {
            "name": "Simple Chat Circuit",
            "description": "Basic circuit for chat testing",
            "data": {
                "nodes": [
                    {
                        "id": "input_node",
                        "type": "input_node",
                        "position": {"x": 0, "y": 0},
                        "data": {}
                    },
                    {
                        "id": "prompt_builder",
                        "type": "prompt_builder",
                        "position": {"x": 100, "y": 0},
                        "data": {"template": "Process this message: {{message}}"}
                    },
                    {
                        "id": "output_node",
                        "type": "output_node",
                        "position": {"x": 200, "y": 0},
                        "data": {"template": "Response: {{output}}"}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "input_node", "target": "prompt_builder"},
                    {"id": "e2", "source": "prompt_builder", "target": "output_node"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Test circuit execution directly
        execute_payload = {
            "inputs": {"message": "Hello, world!"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Process this message: Hello, world!" in data["output"]
        assert "execution_ms" in data
        assert "variables" in data
        assert "logs" in data

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_chat_circuit_with_llm_integration(self, client):
        """Test chat with circuit including LLM connector."""
        # Create circuit with LLM integration
        circuit_data = {
            "name": "Chat LLM Circuit",
            "description": "Circuit with LLM for testing",
            "data": {
                "nodes": [
                    {
                        "id": "input",
                        "type": "input_node",
                        "position": {"x": 0, "y": 0},
                        "data": {}
                    },
                    {
                        "id": "prompt_builder",
                        "type": "prompt_builder",
                        "position": {"x": 100, "y": 0},
                        "data": {"template": "Respond naturally to: {{message}}"}
                    },
                    {
                        "id": "llm_connector",
                        "type": "llm_connector",
                        "position": {"x": 200, "y": 0},
                        "data": {
                            "provider": "echo",  # Use echo for testing
                            "model": "test-model",
                            "temperature": 0.7
                        }
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "prompt_builder"},
                    {"id": "e2", "source": "prompt_builder", "target": "llm_connector"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute circuit
        execute_payload = {
            "inputs": {"message": "How are you?"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "execution_ms" in data
        assert "llm_response" in data["variables"]
        assert isinstance(data["output"], str)

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_with_conditional_logic(self, client):
        """Test circuit with conditional branching logic."""
        # Create circuit with conditional logic
        circuit_data = {
            "name": "Conditional Chat Circuit",
            "description": "Circuit with conditional logic",
            "data": {
                "nodes": [
                    {
                        "id": "input",
                        "type": "input_node",
                        "position": {"x": 0, "y": 0},
                        "data": {}
                    },
                    {
                        "id": "conditional",
                        "type": "conditional",
                        "position": {"x": 100, "y": 0},
                        "data": {"condition": "len(message) > 10"}
                    },
                    {
                        "id": "long_response",
                        "type": "prompt_builder",
                        "position": {"x": 200, "y": 0},
                        "data": {"template": "That's a long message: {{message}}. I see what you mean!"}
                    },
                    {
                        "id": "short_response",
                        "type": "prompt_builder",
                        "position": {"x": 200, "y": 100},
                        "data": {"template": "Brief: {{message}}"}
                    },
                    {
                        "id": "output",
                        "type": "output_node",
                        "position": {"x": 300, "y": 0},
                        "data": {"template": "{{output}}"}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "conditional"},
                    {"id": "e2", "source": "conditional", "target": "long_response", "target_handle": "true"},
                    {"id": "e3", "source": "conditional", "target": "short_response", "target_handle": "false"},
                    {"id": "e4", "source": "long_response", "target": "output"},
                    {"id": "e5", "source": "short_response", "target": "output"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Test with long message (should take true path)
        execute_payload_long = {
            "inputs": {"message": "This is a very long message that should trigger the true condition"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload_long)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "That's a long message:" in data["output"]
        assert "Brief:" not in data["output"]
        assert data["variables"]["condition_result"] is True

        # Test with short message (should take false path)
        execute_payload_short = {
            "inputs": {"message": "Hi"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload_short)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Brief:" in data["output"]
        assert "That's a long message:" not in data["output"]
        assert data["variables"]["condition_result"] is False

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_with_variable_processing(self, client):
        """Test circuit with variable processing nodes."""
        # Create circuit with variable processing
        circuit_data = {
            "name": "Variable Processing Circuit",
            "description": "Circuit with variable processing",
            "data": {
                "nodes": [
                    {
                        "id": "input",
                        "type": "input_node",
                        "position": {"x": 0, "y": 0},
                        "data": {}
                    },
                    {
                        "id": "set_var",
                        "type": "variable_processor",
                        "position": {"x": 100, "y": 0},
                        "data": {"operation": "set", "variable_name": "processed_msg", "value": "PROCESSED: "}
                    },
                    {
                        "id": "append_var",
                        "type": "variable_processor",
                        "position": {"x": 200, "y": 0},
                        "data": {"operation": "append", "variable_name": "processed_msg", "value": "{{message}}"}
                    },
                    {
                        "id": "prompt_builder",
                        "type": "prompt_builder",
                        "position": {"x": 300, "y": 0},
                        "data": {"template": "Final result: {{processed_msg}}"}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "set_var"},
                    {"id": "e2", "source": "set_var", "target": "append_var"},
                    {"id": "e3", "source": "append_var", "target": "prompt_builder"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute circuit
        execute_payload = {
            "inputs": {"message": "Hello"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Final result: PROCESSED: Hello" == data["output"]
        assert data["variables"]["processed_msg"] == "PROCESSED: Hello"

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_execution_timing(self, client):
        """Test circuit execution timing measurements."""
        # Create a simple circuit
        circuit_data = {
            "name": "Timing Test Circuit",
            "description": "For timing measurements",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}}
                ],
                "edges": []
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute circuit multiple times and check timing
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert "execution_ms" in data
        assert isinstance(data["execution_ms"], (int, float))
        assert data["execution_ms"] >= 0

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_log_structure(self, client):
        """Test circuit execution log structure and content."""
        # Create circuit with multiple nodes for richer logging
        circuit_data = {
            "name": "Logging Test Circuit",
            "description": "For log testing",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "var_proc", "type": "variable_processor", "position": {"x": 100, "y": 0},
                     "data": {"operation": "set", "variable_name": "test", "value": "value"}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "var_proc"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute circuit
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)

        # Should have logs for circuit execution start, node executions, and end
        log_events = [log["event"] for log in data["logs"]]
        assert "EXECUTE_CIRCUIT" in log_events
        assert "EXECUTE_NODE_START" in log_events
        assert "EXECUTE_NODE_COMPLETE" in log_events
        assert "EXECUTE_CIRCUIT_COMPLETE" in log_events

        # Check log structure
        for log_entry in data["logs"]:
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "event" in log_entry
            assert "details" in log_entry

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_with_complex_workflow(self, client):
        """Test complex multi-step circuit workflow."""
        # Create complex circuit simulating a full chat pipeline
        circuit_data = {
            "name": "Complex Chat Workflow",
            "description": "Full chat processing workflow",
            "data": {
                "nodes": [
                    # Input processing
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},

                    # Character system prompt
                    {"id": "system_prompt", "type": "system_prompt", "position": {"x": 0, "y": 100},
                     "data": {"text": "You are a helpful assistant."}},

                    # Lore injection
                    {"id": "lore_inject", "type": "lore_injection", "position": {"x": 100, "y": 100},
                     "data": {"keywords": ["help"], "limit": 2}},

                    # Context building
                    {"id": "context_builder", "type": "prompt_builder", "position": {"x": 200, "y": 100},
                     "data": {"template": "Context:\n{{lore_injection}}\n\nUser: {{message}}"}},

                    # Final LLM call
                    {"id": "llm_call", "type": "llm_connector", "position": {"x": 300, "y": 100},
                     "data": {"provider": "echo", "model": "gpt-4", "temperature": 0.7}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "system_prompt"},
                    {"id": "e2", "source": "system_prompt", "target": "lore_inject"},
                    {"id": "e3", "source": "lore_inject", "target": "context_builder"},
                    {"id": "e4", "source": "context_builder", "target": "llm_call"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute complex workflow
        execute_payload = {
            "inputs": {"message": "I need help with something"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "execution_ms" in data
        assert isinstance(data["output"], str)
        assert len(data["variables"]) > 0

        # Check that variables were properly set by each node
        variables = data["variables"]
        assert "lore_injection" in variables
        assert "llm_response" in variables
        assert "prompt" in variables

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_error_handling_in_workflow(self, client):
        """Test error handling in circuit workflow execution."""
        # Create circuit that will likely cause errors
        circuit_data = {
            "name": "Error Handling Test",
            "description": "Circuit for error testing",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    # Invalid LLM connector (unknown provider)
                    {"id": "llm_error", "type": "llm_connector", "position": {"x": 100, "y": 0},
                     "data": {"provider": "invalid_provider", "model": "test"}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "llm_error"}
                ]
            }
        }

        # Create circuit
        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute circuit (should handle error gracefully)
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}

        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert isinstance(data["error"], str)
        assert data["execution_ms"] > 0

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")


class TestCircuitValidationInIntegration:
    """Tests for circuit validation within integrated workflows."""

    def test_validate_working_circuit_before_execution(self, client):
        """Test validating a working circuit before execution."""
        # Create valid circuit
        circuit_data = {
            "name": "Valid Integration Circuit",
            "description": "Valid circuit for integration testing",
            "data": {
                "nodes": [
                    {"id": "start", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "process", "type": "prompt_builder", "position": {"x": 100, "y": 0},
                     "data": {"template": "Processing: {{message}}"}}
                ],
                "edges": [
                    {"id": "e1", "source": "start", "target": "process"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Validate circuit
        validate_response = client.post(f"/circuits/{circuit['id']}/validate")
        assert validate_response.status_code == 200

        validate_data = validate_response.json()
        assert validate_data["valid"] is True
        assert len(validate_data["errors"]) == 0

        # Execute circuit (should work since it's valid)
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}
        execute_response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)
        assert execute_response.status_code == 200

        execute_data = execute_response.json()
        assert execute_data["success"] is True

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_invocation_patterns(self, client):
        """Test different patterns for circuit invocation."""
        # Test 1: Direct circuit execution
        circuit_data = {
            "name": "Invocation Pattern Test",
            "description": "Testing different invocation patterns",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "echo", "type": "prompt_builder", "position": {"x": 100, "y": 0},
                     "data": {"template": "Echo: {{message}}"}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "echo"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Pattern 1: Execute with minimal inputs
        response = client.post(f"/circuits/{circuit['id']}/execute",
                              json={"inputs": {"message": "pattern 1"}})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Pattern 2: Execute with additional metadata
        response = client.post(f"/circuits/{circuit['id']}/execute",
                              json={"inputs": {"message": "pattern 2"},
                                    "character_id": None,
                                    "session_id": "test-session"})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")