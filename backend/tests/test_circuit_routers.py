"""Unit tests for routers/circuits.py - FastAPI circuit endpoints."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database import create_tables
from backend.models import Circuit
from backend.schemas import CircuitCreate


# Setup database for tests
create_tables()


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


class TestCircuitRoutesCRUD:
    """Tests for Circuit CRUD endpoints."""

    def test_list_circuits_empty(self, client):
        """Test listing circuits when none exist."""
        response = client.get("/circuits/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_circuit(self, client):
        """Test creating a new circuit."""
        payload = {
            "name": "Test Circuit",
            "description": "A test circuit",
            "data": {"nodes": [], "edges": []}
        }

        response = client.post("/circuits/", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]
        assert data["data"] == payload["data"]
        assert "id" in data
        assert data["id"] is not None

        # Store ID for cleanup
        created_id = data["id"]

        # Verify it appears in list
        response = client.get("/circuits/")
        assert response.status_code == 200
        circuits = response.json()
        assert len(circuits) == 1
        assert circuits[0]["id"] == created_id

        # Clean up
        client.delete(f"/circuits/{created_id}")

    def test_create_circuit_minimal(self, client):
        """Test creating a circuit with minimal data."""
        payload = {
            "name": "Minimal Circuit",
            "data": {"nodes": [{"id": "node1", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}}], "edges": []}
        }

        response = client.post("/circuits/", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == payload["name"]
        assert data["description"] is None  # Should be null/None
        assert data["data"] == payload["data"]

        # Clean up
        client.delete(f"/circuits/{data['id']}")

    def test_create_circuit_invalid_data(self, client):
        """Test creating a circuit with invalid data."""
        # Missing required 'name'
        payload = {
            "description": "No name provided",
            "data": {"nodes": [], "edges": []}
        }

        response = client.post("/circuits/", json=payload)
        # FastAPI should validate and reject
        assert response.status_code == 422  # Validation error

    def test_get_circuit_existing(self, client):
        """Test getting an existing circuit."""
        # Create a circuit first
        payload = {
            "name": "Get Test Circuit",
            "description": "For get test",
            "data": {"nodes": [], "edges": []}
        }

        create_response = client.post("/circuits/", json=payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Now get it
        response = client.get(f"/circuits/{circuit_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == circuit_id
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]

        # Clean up
        client.delete(f"/circuits/{circuit_id}")

    def test_get_circuit_not_found(self, client):
        """Test getting a non-existent circuit."""
        response = client.get("/circuits/99999")
        assert response.status_code == 404
        assert "Circuit not found" in response.json()["detail"]

    def test_update_circuit(self, client):
        """Test updating an existing circuit."""
        # Create a circuit first
        payload = {
            "name": "Original Name",
            "description": "Original desc",
            "data": {"nodes": [], "edges": []}
        }

        create_response = client.post("/circuits/", json=payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Update it
        update_payload = {
            "name": "Updated Name",
            "description": "Updated description",
            "data": {"nodes": [{"id": "new", "type": "logic", "position": {"x": 100, "y": 100}, "data": {}}], "edges": []}
        }

        response = client.put(f"/circuits/{circuit_id}", json=update_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == circuit_id
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["data"] != payload["data"]  # Should be updated

        # Clean up
        client.delete(f"/circuits/{circuit_id}")

    def test_update_circuit_not_found(self, client):
        """Test updating a non-existent circuit."""
        payload = {"name": "Updated", "data": {"nodes": [], "edges": []}}

        response = client.put("/circuits/99999", json=payload)
        assert response.status_code == 404
        assert "Circuit not found" in response.json()["detail"]

    def test_delete_circuit(self, client):
        """Test deleting a circuit."""
        # Create a circuit first
        payload = {
            "name": "Delete Test",
            "description": "To be deleted",
            "data": {"nodes": [], "edges": []}
        }

        create_response = client.post("/circuits/", json=payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/circuits/{circuit_id}")
        assert response.status_code == 204  # No Content

        # Verify it's gone
        response = client.get(f"/circuits/{circuit_id}")
        assert response.status_code == 404

        # Verify it doesn't appear in list
        response = client.get("/circuits/")
        assert response.status_code == 200
        circuits = response.json()
        assert len([c for c in circuits if c["id"] == circuit_id]) == 0

    def test_delete_circuit_not_found(self, client):
        """Test deleting a non-existent circuit."""
        response = client.delete("/circuits/99999")
        assert response.status_code == 404
        assert "Circuit not found" in response.json()["detail"]


class TestCircuitExecutionRoutes:
    """Tests for Circuit execution endpoints."""

    def test_execute_circuit_success(self, client):
        """Test successfully executing a circuit."""
        # Create a simple circuit first
        circuit_payload = {
            "name": "Execution Test",
            "description": "For execution test",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "prompt", "type": "prompt_builder", "position": {"x": 100, "y": 0}, "data": {"template": "Hello {{name}}"}},
                    {"id": "output", "type": "output_node", "position": {"x": 200, "y": 0}, "data": {"template": "Final output"}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "prompt"},
                    {"id": "e2", "source": "prompt", "target": "output"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Execute the circuit
        execution_payload = {
            "inputs": {"name": "World"},
            "character_id": None,
            "session_id": None
        }

        response = client.post(f"/circuits/{circuit_id}/execute", json=execution_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "execution_ms" in data
        assert "output" in data
        assert "variables" in data
        assert "logs" in data
        assert data["output"] == "Hello World" or "Final output" in data["output"]

        # Clean up
        client.delete(f"/circuits/{circuit_id}")

    def test_execute_circuit_not_found(self, client):
        """Test executing a non-existent circuit."""
        execution_payload = {
            "inputs": {"message": "test"},
            "character_id": None
        }

        response = client.post("/circuits/99999/execute", json=execution_payload)
        assert response.status_code == 404
        assert "Circuit not found" in response.json()["detail"]

    def test_execute_circuit_validation_failure(self, client):
        """Test executing a circuit that fails validation."""
        # Create a circuit with cycle (invalid)
        circuit_payload = {
            "name": "Invalid Execution Test",
            "description": "Circuit with cycle",
            "data": {
                "nodes": [
                    {"id": "node1", "type": "logic", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "node2", "type": "logic", "position": {"x": 100, "y": 0}, "data": {}}
                ],
                "edges": [
                    {"id": "e1", "source": "node1", "target": "node2"},
                    {"id": "e2", "source": "node2", "target": "node1"}  # Cycle
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Execute (should fail validation)
        execution_payload = {
            "inputs": {},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit_id}/execute", json=execution_payload)
        assert response.status_code == 200  # Execution endpoint handles errors gracefully

        data = response.json()
        assert data["success"] is False
        assert "cycles" in data["error"].lower() or "validation" in data["error"].lower()

        # Clean up
        client.delete(f"/circuits/{circuit_id}")

    def test_execute_circuit_with_error(self, client):
        """Test executing a circuit that causes runtime error."""
        # Create a circuit that will cause LLM error
        circuit_payload = {
            "name": "Error Execution Test",
            "description": "Circuit that causes error",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "llm", "type": "llm_connector", "position": {"x": 100, "y": 0}, "data": {"provider": "unknown", "model": "test"}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "llm"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        execution_payload = {
            "inputs": {"prompt": "test"},
            "character_id": None
        }

        response = client.post(f"/circuits/{circuit_id}/execute", json=execution_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "execution_ms" in data

        # Clean up
        client.delete(f"/circuits/{circuit_id}")


class TestCircuitValidationRoutes:
    """Tests for Circuit validation endpoints."""

    def test_validate_circuit_endpoint(self, client):
        """Test validating a circuit via API endpoint."""
        # Create a circuit first
        circuit_payload = {
            "name": "Validation Test",
            "description": "For validation test",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "prompt", "type": "prompt_builder", "position": {"x": 100, "y": 0}, "data": {"template": "Hello {{name}}"}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "prompt"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Validate it
        response = client.post(f"/circuits/{circuit_id}/validate")
        assert response.status_code == 200

        data = response.json()
        assert "valid" in data
        assert "errors" in data
        assert "node_count" in data
        assert "edge_count" in data
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        assert data["node_count"] == 2
        assert data["edge_count"] == 1

        # Clean up
        client.delete(f"/circuits/{circuit_id}")

    def test_validate_circuit_not_found(self, client):
        """Test validating a non-existent circuit."""
        response = client.post("/circuits/99999/validate")
        assert response.status_code == 404
        assert "Circuit not found" in response.json()["detail"]

    def test_validate_circuit_invalid(self, client):
        """Test validating an invalid circuit."""
        # Create invalid circuit (with cycle)
        circuit_payload = {
            "name": "Invalid Validation Test",
            "description": "Circuit with cycle",
            "data": {
                "nodes": [
                    {"id": "node1", "type": "logic", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "node2", "type": "logic", "position": {"x": 100, "y": 0}, "data": {}}
                ],
                "edges": [
                    {"id": "e1", "source": "node1", "target": "node2"},
                    {"id": "e2", "source": "node2", "target": "node1"}  # Cycle
                ]
            }
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        # Validate (should be invalid)
        response = client.post(f"/circuits/{circuit_id}/validate")
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert "cycle" in data["errors"][0].lower()

        # Clean up
        client.delete(f"/circuits/{circuit_id}")

    def test_validate_raw_circuit(self, client):
        """Test validating raw circuit data."""
        raw_data = {
            "nodes": [
                {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "prompt", "type": "prompt_builder", "position": {"x": 100, "y": 0}, "data": {"template": "Hello"}}
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "prompt"}
            ]
        }

        response = client.post("/circuits/validate-raw", json=raw_data)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        assert data["node_count"] == 2
        assert data["edge_count"] == 1

    def test_validate_raw_circuit_empty(self, client):
        """Test validating empty raw circuit data."""
        raw_data = {"nodes": [], "edges": []}

        response = client.post("/circuits/validate-raw", json=raw_data)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is False  # Should require at least one entry node
        assert len(data["errors"]) > 0
        assert "entry node" in data["errors"][0]

    def test_validate_raw_circuit_invalid_format(self, client):
        """Test validating malformed raw circuit data."""
        raw_data = {"invalid": "format"}

        response = client.post("/circuits/validate-raw", json=raw_data)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0


class TestCircuitIntegration:
    """Tests for circuit integration with other systems."""

    def test_execute_circuit_with_character_integration(self, client):
        """Test executing circuit with character integration."""
        # This would require setting up a character in the database
        # For now, just test that the endpoint accepts the parameter
        circuit_payload = {
            "name": "Character Integration Test",
            "data": {
                "nodes": [{"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}}],
                "edges": []
            }
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit_id = create_response.json()["id"]

        execution_payload = {
            "inputs": {"message": "test"},
            "character_id": 1,  # May not exist, but API should handle it
            "session_id": "test-session"
        }

        response = client.post(f"/circuits/{circuit_id}/execute", json=execution_payload)
        assert response.status_code == 200

        data = response.json()
        # Should complete, even if character integration fails
        assert "success" in data
        assert "execution_ms" in data

        # Clean up
        client.delete(f"/circuits/{circuit_id}")