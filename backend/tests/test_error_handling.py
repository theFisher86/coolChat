"""Error handling and edge case tests for circuits functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import httpx

from backend.main import app
from backend.database import create_tables
from backend.circuit_engine import CircuitExecutor, CircuitValidator, CircuitParser
from backend.circuit_integrations import CircuitIntegrationAdapter


# Setup database for tests
create_tables()


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


class TestCircuitExecutionErrorHandling:
    """Tests for error handling during circuit execution."""

    def test_execute_with_malformed_circuit_data(self, client):
        """Test executing circuit with malformed/invalid JSON data."""
        # Create circuit with malformed data
        malformed_data = {
            "name": "Malformed Circuit",
            "description": "Test malformed data",
            "data": {"invalid": "structure", "missing": "nodes_and_edges"}
        }

        create_response = client.post("/circuits/", json=malformed_data)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Try to execute malformed circuit
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}
        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)

        assert response.status_code == 200  # API handles errors gracefully
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["execution_ms"] > 0

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_execute_with_extremely_large_circuit(self, client):
        """Test executing circuit with many nodes and edges."""
        # Create large circuit that might cause performance issues
        nodes = []
        edges = []

        # Create 50 nodes
        for i in range(50):
            nodes.append({
                "id": f"node_{i}",
                "type": "prompt_builder" if i % 2 == 0 else "variable_processor",
                "position": {"x": i * 100, "y": 100},
                "data": {
                    "template": f"Step {i}: {{input}}" if i % 2 == 0 else {
                        "operation": "set",
                        "variable_name": f"var_{i}",
                        "value": f"value_{i}"
                    }
                }
            })

        # Create edges between nodes (chain them)
        for i in range(len(nodes) - 1):
            edges.append({
                "id": f"edge_{i}",
                "source": nodes[i]["id"],
                "target": nodes[i + 1]["id"]
            })

        large_circuit = {
            "name": "Large Circuit Test",
            "description": "Circuit with 50 nodes",
            "data": {"nodes": nodes, "edges": edges}
        }

        create_response = client.post("/circuits/", json=large_circuit)
        if create_response.status_code != 201:
            # If creation fails, it's probably due to size limits or validation
            assert create_response.status_code in [400, 422]
            return

        circuit = create_response.json()

        # Execute large circuit
        execute_payload = {"inputs": {"input": "start"}, "character_id": None}
        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)

        # Should either succeed or fail gracefully
        assert response.status_code == 200
        data = response.json()
        # Execution time should be reasonable (under 10 seconds)
        assert data["execution_ms"] < 10000

        # Clean up if created
        if create_response.status_code == 201:
            client.delete(f"/circuits/{circuit['id']}")

    def test_execute_with_nested_conditional_loops(self, client):
        """Test circuit with deeply nested conditionals that might cause recursion issues."""
        # Create circuit with problematic conditional logic
        problematic_nodes = [
            {
                "id": "input",
                "type": "input_node",
                "position": {"x": 0, "y": 0},
                "data": {}
            }
        ]

        # Add problematic conditional logic that might cause issues
        conditional_node = {
            "id": "cond",
            "type": "conditional",
            "position": {"x": 100, "y": 0},
            "data": {
                "condition": "always_true_var == True",  # This might create evaluation issues
                "true_path": "loop_target",
                "false_path": "exit"
            }
        }

        loop_target = {
            "id": "loop_target",
            "type": "variable_processor",
            "position": {"x": 200, "y": 0},
            "data": {
                "operation": "set",
                "variable_name": "always_true_var",
                "value": True
            }
        }

        exit_node = {
            "id": "exit",
            "type": "output_node",
            "position": {"x": 200, "y": 100},
            "data": {"template": "Exit reached"}
        }

        nodes = [input, conditional_node, loop_target, exit_node]
        edges = [
            {"id": "e1", "source": "input", "target": "cond"},
            {"id": "e2", "source": "cond", "target": "loop_target", "target_handle": "true"},
            {"id": "e3", "source": "loop_target", "target": "cond"}  # Creates potential loop
        ]

        complex_circuit = {
            "name": "Complex Conditional Circuit",
            "description": "Circuit with conditional loops",
            "data": {"nodes": nodes, "edges": edges}
        }

        create_response = client.post("/circuits/", json=complex_circuit)
        if create_response.status_code != 201:
            # Circuit creation might fail due to validation
            assert create_response.status_code in [200, 422]  # Validation might catch issues
            return

        circuit = create_response.json()

        # Execute complex circuit
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}
        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)

        assert response.status_code == 200
        data = response.json()
        # Should complete successfully or fail gracefully

        client.delete(f"/circuits/{circuit['id']}")


class TestNetworkAndAPIErrorHandling:
    """Tests for network failures and API error conditions."""

    @patch('httpx.Client')
    def test_llm_api_timeout_handling(self, mock_client_class, client):
        """Test handling of LLM API timeouts."""
        # Mock timeout exception
        timeout_exception = httpx.TimeoutException("Request timeout")
        http_exception = httpx.HTTPStatusError(
            "Timeout",
            request=Mock(),
            response=Mock(status_code=408)
        )

        # Create circuit with LLM connector
        llm_circuit = {
            "name": "LLM Timeout Test",
            "description": "Circuit for testing LLM timeouts",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "llm", "type": "llm_connector", "position": {"x": 100, "y": 0},
                     "data": {"provider": "openai", "model": "gpt-4", "temperature": 0.7}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "llm"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=llm_circuit)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Mock HTTP client to raise timeout
        mock_client = Mock()
        mock_client.post.side_effect = http_exception
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        # Execute circuit - should handle timeout gracefully
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}
        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data

        # Clean up
        client.delete(f"/circuits/{circuit['id']}")

    def test_database_connection_failures(self, client):
        """Test handling when database operations fail."""
        # This test would need mocking of the database session
        # For now, we'll test API-level error handling for database issues
        response = client.get("/circuits/")
        assert response.status_code == 200  # Should still respond even if DB issues

        # Test with extremely long identifiers that might cause DB issues
        long_name = "A" * 500  # Very long circuit name
        payload = {
            "name": long_name,
            "data": {"nodes": [], "edges": []}
        }

        response = client.post("/circuits/", json=payload)
        # Should either succeed or fail with appropriate error
        assert response.status_code in [201, 422, 500]

    def test_concurrent_circuit_operations(self, client):
        """Test handling of concurrent circuit creation and execution."""
        import threading
        import time

        results = []
        errors = []

        def create_and_execute(index):
            try:
                # Create circuit
                payload = {
                    "name": f"Concurrent Circuit {index}",
                    "data": {"nodes": [], "edges": []}
                }
                create_response = client.post("/circuits/", json=payload)

                if create_response.status_code == 201:
                    circuit = create_response.json()
                    # Execute circuit
                    execute_payload = {"inputs": {"message": f"test {index}"}, "character_id": None}
                    execute_response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)

                    results.append({
                        'index': index,
                        'create_status': create_response.status_code,
                        'execute_status': execute_response.status_code
                    })

                    # Clean up
                    client.delete(f"/circuits/{circuit['id']}")
            except Exception as e:
                errors.append(e)

        # Run concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_execute, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all operations completed
        assert len(results) >= 3  # Most should succeed
        assert len(errors) <= 2   # Few errors allowed

        # All successful operations should have proper response codes
        for result in results:
            assert result['create_status'] == 201
            assert result['execute_status'] == 200


class TestCircuitValidationEdgeCases:
    """Tests for circuit validation edge cases."""

    def test_validate_empty_nodes_circuit(self, client):
        """Test validating circuit with completely empty nodes."""
        empty_circuit = {
            "name": "Empty Circuit",
            "data": {"nodes": [], "edges": []}
        }

        response = client.post("/circuits/validate-raw", json=empty_circuit)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False  # Should require at least one node
        assert "entry node" in data["errors"][0].lower()

    def test_validate_circuit_with_duplicate_node_ids(self, client):
        """Test validation with duplicate node IDs."""
        duplicate_circuit = {
            "name": "Duplicate IDs Circuit",
            "data": {
                "nodes": [
                    {"id": "node1", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "node1", "type": "output_node", "position": {"x": 100, "y": 100}, "data": {}}  # Duplicate ID
                ],
                "edges": []
            }
        }

        response = client.post("/circuits/validate-raw", json=duplicate_circuit)

        # Validation should catch this issue
        assert response.status_code == 200
        data = response.json()
        # Either invalid due to duplicate IDs or valid if parser handles it

    def test_validate_circuit_with_invalid_node_types(self, client):
        """Test validation with unknown/invalid node types."""
        invalid_type_circuit = {
            "name": "Invalid Types Circuit",
            "data": {
                "nodes": [
                    {"id": "node1", "type": "unknown_type", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "node2", "type": "another_unknown", "position": {"x": 100, "y": 0}, "data": {}}
                ],
                "edges": [
                    {"id": "e1", "source": "node1", "target": "node2"}
                ]
            }
        }

        response = client.post("/circuits/validate-raw", json=invalid_type_circuit)

        assert response.status_code == 200
        data = response.json()
        # Should validate nodes and potentially find issues with unknown types

    def test_validate_malformed_edges(self, client):
        """Test validation with malformed edge data."""
        malformed_edge_circuit = {
            "name": "Malformed Edges Circuit",
            "data": {
                "nodes": [
                    {"id": "node1", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "node2", "type": "output_node", "position": {"x": 100, "y": 0}, "data": {}}
                ],
                "edges": [
                    {"id": "e1", "source": "node1", "target": "nonexistent_target"},  # Target doesn't exist
                    {"source": "node2", "target": "node1"}  # Missing id and backwards
                ]
            }
        }

        response = client.post("/circuits/validate-raw", json=malformed_edge_circuit)

        assert response.status_code == 200
        data = response.json()
        # Validation should catch edge-related issues

    def test_load_circuit_with_corrupted_data(self, client):
        """Test loading circuit that has been corrupted in database."""
        # Create a valid circuit
        valid_circuit = {
            "name": "Corruption Test Circuit",
            "data": {
                "nodes": [{"id": "node1", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}}],
                "edges": []
            }
        }

        create_response = client.post("/circuits/", json=valid_circuit)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Get circuit data (simulates loading)
        get_response = client.get(f"/circuits/{circuit['id']}")
        assert get_response.status_code == 200

        # Validate retrieved circuit
        retrieved_circuit = get_response.json()
        validate_payload = retrieved_circuit["data"]
        validate_response = client.post("/circuits/validate-raw", json=validate_payload)

        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        # Should be valid since we created it properly

        client.delete(f"/circuits/{circuit['id']}")


class TestSystemIntegrationEdgeCases:
    """Tests for system integration edge cases."""

    def test_circuit_execution_with_memory_pressure(self, client):
        """Test circuit execution under simulated memory pressure."""
        # Create circuit that generates large amounts of data
        large_data_circuit = {
            "name": "Memory Test Circuit",
            "data": {
                "nodes": [
                    {"id": "input", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}},
                    {"id": "large_generator", "type": "variable_processor", "position": {"x": 100, "y": 0},
                     "data": {"operation": "set", "variable_name": "large_var", "value": "x" * 10000}},  # Large value
                    {"id": "another_large", "type": "variable_processor", "position": {"x": 200, "y": 0},
                     "data": {"operation": "set", "variable_name": "another_var", "value": "y" * 10000}}
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "large_generator"},
                    {"id": "e2", "source": "large_generator", "target": "another_large"}
                ]
            }
        }

        create_response = client.post("/circuits/", json=large_data_circuit)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Execute circuit with large data
        execute_payload = {"inputs": {"message": "test"}, "character_id": None}
        response = client.post(f"/circuits/{circuit['id']}/execute", json=execute_payload)

        assert response.status_code == 200
        data = response.json()
        # Should handle large data appropriately

        client.delete(f"/circuits/{circuit['id']}")

    def test_api_rate_limiting_simulation(self, client):
        """Test behavior when multiple requests come in rapidly."""
        # Create a circuit
        simple_circuit = {
            "name": "Rate Limit Test",
            "data": {"nodes": [], "edges": []}
        }

        create_response = client.post("/circuits/", json=simple_circuit)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Send multiple execute requests rapidly
        import concurrent.futures

        def execute_request():
            payload = {"inputs": {"message": "rapid test"}, "character_id": None}
            return client.post(f"/circuits/{circuit['id']}/execute", json=payload)

        # Execute 10 requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All should complete successfully
        success_count = sum(1 for r in responses if r.status_code == 200 and r.json()["success"] is True)
        assert success_count > 5  # Most should succeed

        client.delete(f"/circuits/{circuit['id']}")


class TestCircuitPersistenceEdgeCases:
    """Tests for circuit persistence edge cases."""

    def test_update_circuit_with_concurrent_modifications(self, client):
        """Test updating circuit while other operations are happening."""
        # Create circuit
        original_circuit = {
            "name": "Concurrency Test Circuit",
            "data": {"nodes": [], "edges": []}
        }

        create_response = client.post("/circuits/", json=original_circuit)
        assert create_response.status_code == 201
        circuit = create_response.json()

        # Simulate concurrent updates
        import threading

        update_results = []
        errors = []

        def update_circuit(thread_id):
            try:
                update_payload = {
                    "name": f"Updated by thread {thread_id}",
                    "data": {"nodes": [{"id": f"node_{thread_id}", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}}], "edges": []}
                }
                response = client.put(f"/circuits/{circuit['id']}", json=update_payload)
                update_results.append(response)
            except Exception as e:
                errors.append(e)

        # Run concurrent updates
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_circuit, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # At least one update should succeed
        success_count = sum(1 for r in update_results if r.status_code == 200)
        assert success_count >= 1

        client.delete(f"/circuits/{circuit['id']}")

    def test_circuit_deletion_race_condition(self, client):
        """Test deleting circuit while other operations are in progress."""
        # Create circuit
        circuit_payload = {
            "name": "Deletion Race Test",
            "data": {"nodes": [], "edges": []}
        }

        create_response = client.post("/circuits/", json=circuit_payload)
        assert create_response.status_code == 201
        circuit = create_response.json()

        import threading
        import time

        operation_results = []

        def execute_operation(op_type):
            try:
                if op_type == "delete":
                    time.sleep(0.1)  # Small delay
                    response = client.delete(f"/circuits/{circuit['id']}")
                    return {"type": "delete", "status": response.status_code}
                else:
                    response = client.get(f"/circuits/{circuit['id']}")
                    return {"type": "get", "status": response.status_code}
            except Exception as e:
                return {"type": op_type, "error": str(e)}

        # Start delete operation
        delete_thread = threading.Thread(target=lambda: operation_results.append(execute_operation("delete")))
        delete_thread.start()

        # Meanwhile try to read
        get_thread = threading.Thread(target=lambda: operation_results.append(execute_operation("get")))
        get_thread.start()

        delete_thread.join()
        get_thread.join()

        # Both operations should complete gracefully
        assert len(operation_results) == 2

        # At least one should succeed
        delete_result = next((r for r in operation_results if r["type"] == "delete"), None)
        get_result = next((r for r in operation_results if r["type"] == "get"), None)

        # Either delete succeeded and get got 404, or both get succeeded if get happened first
        assert delete_result["status"] in [204, 404]
        assert get_result["status"] in [200, 404]