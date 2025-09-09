"""Unit tests for circuit_engine.py - Circuit execution engine components."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.circuit_engine import (
    CircuitParser,
    CircuitValidator,
    CircuitExecutor,
    NodeData,
    Edge,
    CircuitData,
    ExecutionContext,
    CircuitParser,
    CircuitValidator,
    CircuitExecutor,
    ExecutionContext,
)


class TestCircuitParser:
    """Tests for CircuitParser class."""

    def test_parse_circuit_valid_data(self):
        """Test parsing valid circuit data with nodes and edges."""
        data = {
            "nodes": [
                {
                    "id": "node1",
                    "type": "input_node",
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "Input"}
                },
                {
                    "id": "node2",
                    "type": "output_node",
                    "position": {"x": 200, "y": 200},
                    "data": {"label": "Output"}
                }
            ],
            "edges": [
                {
                    "id": "edge1",
                    "source": "node1",
                    "target": "node2"
                }
            ]
        }

        circuit_data = CircuitParser.parse_circuit(data)

        assert len(circuit_data.nodes) == 2
        assert len(circuit_data.edges) == 1
        assert circuit_data.nodes[0].id == "node1"
        assert circuit_data.nodes[1].id == "node2"
        assert circuit_data.nodes_by_id["node1"].type == "input_node"
        assert circuit_data.nodes_by_id["node2"].type == "output_node"
        assert circuit_data.edges_by_source["node1"][0].target == "node2"
        assert circuit_data.edges_by_target["node2"][0].source == "node1"

    def test_parse_circuit_empty_data(self):
        """Test parsing empty circuit data."""
        data = {"nodes": [], "edges": []}

        circuit_data = CircuitParser.parse_circuit(data)

        assert len(circuit_data.nodes) == 0
        assert len(circuit_data.edges) == 0
        assert len(circuit_data.nodes_by_id) == 0
        assert len(circuit_data.edges_by_source) == 0
        assert len(circuit_data.edges_by_target) == 0

    def test_parse_circuit_missing_edges(self):
        """Test parsing circuit data without edges."""
        data = {
            "nodes": [
                {
                    "id": "node1",
                    "type": "input_node",
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "Input"}
                }
            ]
        }

        circuit_data = CircuitParser.parse_circuit(data)

        assert len(circuit_data.nodes) == 1
        assert len(circuit_data.edges) == 0
        assert circuit_data.nodes_by_id["node1"]
        assert len(circuit_data.edges_by_source) == 0
        assert len(circuit_data.edges_by_target) == 0

    def test_parse_circuit_complex_connections(self):
        """Test parsing circuit with multiple incoming/outgoing edges."""
        data = {
            "nodes": [
                {"id": "n1", "type": "logic", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "logic", "position": {"x": 100, "y": 0}, "data": {}},
                {"id": "n3", "type": "logic", "position": {"x": 200, "y": 0}, "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2"},
                {"id": "e2", "source": "n1", "target": "n3"},
                {"id": "e3", "source": "n2", "target": "n3"}
            ]
        }

        circuit_data = CircuitParser.parse_circuit(data)

        assert len(circuit_data.nodes) == 3
        assert len(circuit_data.edges) == 3
        assert len(circuit_data.edges_by_source["n1"]) == 2
        assert len(circuit_data.edges_by_target["n3"]) == 2


class TestCircuitValidator:
    """Tests for CircuitValidator class."""

    def test_validate_node_conditional_valid(self):
        """Test validating valid conditional node."""
        node = NodeData(
            id="test",
            type="conditional",
            position={"x": 0, "y": 0},
            data={"condition": "true == true", "true_path": "path1", "false_path": "path2"}
        )

        errors = CircuitValidator.validate_node(node)
        assert len(errors) == 0

    def test_validate_node_conditional_missing_condition(self):
        """Test validating conditional node without condition."""
        node = NodeData(
            id="test",
            type="conditional",
            position={"x": 0, "y": 0},
            data={}
        )

        errors = CircuitValidator.validate_node(node)
        assert len(errors) == 1
        assert "missing 'condition' field" in errors[0]

    def test_validate_node_llm_missing_provider(self):
        """Test validating LLM connector node without provider."""
        node = NodeData(
            id="test",
            type="llm_connector",
            position={"x": 0, "y": 0},
            data={"model": "gpt-4"}
        )

        errors = CircuitValidator.validate_node(node)
        assert len(errors) == 1
        assert "missing 'provider' field" in errors[0]

    def test_validate_node_prompt_builder_missing_template(self):
        """Test validating prompt builder node without template."""
        node = NodeData(
            id="test",
            type="prompt_builder",
            position={"x": 0, "y": 0},
            data={}
        )

        errors = CircuitValidator.validate_node(node)
        assert len(errors) == 1
        assert "missing template" in errors[0]

    def test_validate_circuit_no_start_nodes(self):
        """Test validating circuit with no start nodes."""
        circuit_data = CircuitData(
            nodes=[
                NodeData(id="n1", type="logic", position={"x": 0, "y": 0}, data={}),
                NodeData(id="n2", type="logic", position={"x": 100, "y": 0}, data={})
            ],
            edges=[
                Edge(id="e1", source="n1", target="n2")
            ],
            nodes_by_id={"n1": Mock(type="logic"), "n2": Mock(type="logic")},
            edges_by_source={"n1": [Mock(target="n2")]},
            edges_by_target={"n2": [Mock(source="n1")]}
        )

        errors = CircuitValidator.validate_circuit(circuit_data)
        assert len(errors) == 1
        assert "at least one entry node" in errors[0]

    def test_validate_circuit_with_start_node(self):
        """Test validating circuit with proper start node."""
        circuit_data = CircuitData(
            nodes=[
                NodeData(id="n1", type="input_node", position={"x": 0, "y": 0}, data={}),
                NodeData(id="n2", type="logic", position={"x": 100, "y": 0}, data={})
            ],
            edges=[
                Edge(id="e1", source="n1", target="n2")
            ],
            nodes_by_id={"n1": Mock(type="input_node"), "n2": Mock(type="logic")},
            edges_by_source={"n1": [Mock(target="n2")]},
            edges_by_target={"n2": [Mock(source="n1")]}
        )

        errors = CircuitValidator.validate_circuit(circuit_data)
        assert len(errors) == 0

    def test_validate_circuit_with_cycle(self):
        """Test detecting cycles in circuit."""
        circuit_data = CircuitData(
            nodes=[
                NodeData(id="n1", type="logic", position={"x": 0, "y": 0}, data={}),
                NodeData(id="n2", type="logic", position={"x": 100, "y": 0}, data={})
            ],
            edges=[
                Edge(id="e1", source="n1", target="n2"),
                Edge(id="e2", source="n2", target="n1")  # Cycle
            ],
            nodes_by_id={"n1": Mock(type="logic", id="n1"), "n2": Mock(type="logic", id="n2")},
            edges_by_source={
                "n1": [Mock(target="n2")],
                "n2": [Mock(target="n1")]
            },
            edges_by_target={
                "n1": [Mock(source="n2")],
                "n2": [Mock(source="n1")]
            }
        )

        errors = CircuitValidator.validate_circuit(circuit_data)
        assert len(errors) == 1
        assert "contains cycles" in errors[0]


class TestCircuitExecutor:
    """Tests for CircuitExecutor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.executor = CircuitExecutor(db=self.mock_db)

    def test_execute_circuit_success(self, mocker):
        """Test successful circuit execution."""
        mock_circuit = Mock()
        mock_circuit.id = 1
        mock_circuit.data = {
            "nodes": [
                {"id": "start", "type": "input_node", "position": {"x": 0, "y": 0}, "data": {}}
            ],
            "edges": []
        }

        # Mock parser and validator
        mocker.patch('backend.circuit_engine.CircuitParser.parse_circuit')
        mocker.patch('backend.circuit_engine.CircuitValidator.validate_circuit', return_value=[])

        # Mock _execute_node method
        mocker.patch.object(self.executor, '_execute_node')

        inputs = {"message": "test"}
        result = self.executor.execute_circuit(mock_circuit, inputs)

        assert result["success"] is True
        assert "execution_ms" in result
        assert "output" in result

    def test_execute_circuit_validation_failure(self, mocker):
        """Test circuit execution with validation failure."""
        mock_circuit = Mock()
        mock_circuit.data = {"nodes": [], "edges": []}

        mocker.patch('backend.circuit_engine.CircuitParser.parse_circuit')
        mocker.patch('backend.circuit_engine.CircuitValidator.validate_circuit',
                    return_value=["Validation error"])

        inputs = {"message": "test"}
        result = self.executor.execute_circuit(mock_circuit, inputs)

        assert result["success"] is False
        assert "Validation error" in result["error"]
        assert "execution_ms" in result

    def test_execute_circuit_execution_error(self, mocker):
        """Test circuit execution with runtime error."""
        mock_circuit = Mock()
        mock_circuit.data = {"nodes": [], "edges": []}

        mocker.patch('backend.circuit_engine.CircuitParser.parse_circuit',
                    side_effect=Exception("Parse error"))
        mocker.patch('backend.circuit_engine.CircuitValidator.validate_circuit', return_value=[])

        inputs = {"message": "test"}
        result = self.executor.execute_circuit(mock_circuit, inputs)

        assert result["success"] is False
        assert "Parse error" in result["error"]
        assert "execution_ms" in result

    def test_execute_node_input_node(self, mocker):
        """Test executing input_node."""
        node = NodeData(
            id="input1",
            type="input_node",
            position={"x": 0, "y": 0},
            data={}
        )

        context = ExecutionContext(
            variables={"existing": "value"},
            output=[],
            logs=[]
        )

        circuit_data = CircuitData(
            nodes=[node],
            edges=[],
            nodes_by_id={"input1": node},
            edges_by_source={},
            edges_by_target={}
        )

        # Mock logging
        mock_log = mocker.patch.object(self.executor, '_log_event')

        result = self.executor._execute_node_logic(node, context)

        assert result == {"variables": {"existing": "value"}}
        mock_log.assert_called()

    def test_execute_node_variable_processor_set(self, mocker):
        """Test executing variable processor with set operation."""
        node = NodeData(
            id="var1",
            type="variable_processor",
            position={"x": 0, "y": 0},
            data={"operation": "set", "variable_name": "test_var", "value": "test_value"}
        )

        context = ExecutionContext(variables={}, output=[], logs=[])

        mock_log = mocker.patch.object(self.executor, '_log_event')

        result = self.executor._execute_node_logic(node, context)

        assert context.variables["test_var"] == "test_value"
        assert result == {"variables": {"test_var": "test_value"}}
        mock_log.assert_called()

    def test_execute_node_variable_processor_append(self, mocker):
        """Test executing variable processor with append operation."""
        node = NodeData(
            id="var2",
            type="variable_processor",
            position={"x": 0, "y": 0},
            data={"operation": "append", "variable_name": "test_var", "value": " suffix"}
        )

        context = ExecutionContext(variables={"test_var": "prefix"}, output=[], logs=[])

        mock_log = mocker.patch.object(self.executor, '_log_event')

        result = self.executor._execute_node_logic(node, context)

        assert context.variables["test_var"] == "prefix suffix"
        assert result == {"variables": {"test_var": "prefix suffix"}}

    def test_execute_node_variable_processor_append_new_var(self, mocker):
        """Test executing variable processor with append operation on new variable."""
        node = NodeData(
            id="var3",
            type="variable_processor",
            position={"x": 0, "y": 0},
            data={"operation": "append", "variable_name": "new_var", "value": "value"}
        )

        context = ExecutionContext(variables={}, output=[], logs=[])

        mock_log = mocker.patch.object(self.executor, '_log_event')

        result = self.executor._execute_node_logic(node, context)

        assert context.variables["new_var"] == "value"
        assert result == {"variables": {"new_var": "value"}}

    def test_execute_node_conditional_true(self, mocker):
        """Test executing conditional node with true result."""
        node = NodeData(
            id="cond1",
            type="conditional",
            position={"x": 0, "y": 0},
            data={"condition": "flag==true"}
        )

        context = ExecutionContext(variables={"flag": True}, output=[], logs=[])

        mock_log = mocker.patch.object(self.executor, '_log_event')
        mock_eval = mocker.patch.object(self.executor, '_evaluate_condition', return_value=True)

        result = self.executor._execute_node_logic(node, context)

        assert context.variables["condition_result"] is True
        assert result == {"variables": {"condition_result": True}}
        mock_eval.assert_called_with("flag==true", {"flag": True})

    def test_execute_node_prompt_builder(self, mocker):
        """Test executing prompt builder node."""
        node = NodeData(
            id="prompt1",
            type="prompt_builder",
            position={"x": 0, "y": 0},
            data={"template": "Hello {{name}}, your age is {{age}}"}
        )

        context = ExecutionContext(
            variables={"name": "John", "age": 30, "other": "ignore"},
            output=[],
            logs=[]
        )

        mock_log = mocker.patch.object(self.executor, '_log_event')

        result = self.executor._execute_node_logic(node, context)

        assert context.variables["prompt"] == "Hello John, your age is 30"
        assert "output" in result
        assert "variables" in result
        mock_log.assert_called()

    def test_execute_node_llm_connector(self, mocker):
        """Test executing LLM connector node."""
        node = NodeData(
            id="llm1",
            type="llm_connector",
            position={"x": 0, "y": 0},
            data={"provider": "openai", "model": "gpt-4"}
        )

        context = ExecutionContext(
            variables={"prompt": "Test prompt"},
            output=[],
            logs=[]
        )

        mock_log = mocker.patch.object(self.executor, '_log_event')
        mock_call_llm = mocker.patch.object(self.executor.integrator, 'call_llm',
                                          return_value="LLM response")

        result = self.executor._execute_node_logic(node, context, character_id=1)

        assert context.variables["llm_response"] == "LLM response"
        assert result == {"output": "LLM response", "variables": {"llm_response": "LLM response"}}
        mock_call_llm.assert_called_with("openai", "gpt-4", "Test prompt", 1)

    def test_execute_node_llm_connector_no_prompt(self, mocker):
        """Test executing LLM connector node without prompt."""
        node = NodeData(
            id="llm2",
            type="llm_connector",
            position={"x": 0, "y": 0},
            data={"provider": "openai", "model": "gpt-4"}
        )

        context = ExecutionContext(variables={}, output=[], logs=[])

        mock_log = mocker.patch.object(self.executor, '_log_event')

        with pytest.raises(ValueError, match="No prompt available"):
            self.executor._execute_node_logic(node, context)

    def test_execute_node_lore_injection(self, mocker):
        """Test executing lore injection node."""
        node = NodeData(
            id="lore1",
            type="lore_injection",
            position={"x": 0, "y": 0},
            data={"keywords": ["magic"], "limit": 3}
        )

        context = ExecutionContext(variables={}, output=[], logs=[])
        mock_lore_entries = [
            {"id": 1, "keyword": "magic", "content": "Magic content", "score": 0.9}
        ]

        mock_log = mocker.patch.object(self.executor, '_log_event')
        mock_query_lore = mocker.patch.object(self.executor.integrator, 'query_lore',
                                            return_value=mock_lore_entries)

        result = self.executor._execute_node_logic(node, context)

        expected_lore = "[magic]: Magic content"
        assert context.variables["lore_injection"] == expected_lore
        assert result == {"output": expected_lore, "variables": {"lore_injection": expected_lore}}
        mock_query_lore.assert_called_with(["magic"], 3)

    def test_execute_node_system_prompt(self, mocker):
        """Test executing system prompt node."""
        node = NodeData(
            id="system1",
            type="system_prompt",
            position={"x": 0, "y": 0},
            data={"text": "You are a helpful assistant."}
        )

        context = ExecutionContext(variables={}, output=[], logs=[])

        mock_log = mocker.patch.object(self.executor, '_log_event')

        result = self.executor._execute_node_logic(node, context)

        assert context.variables["system_prompt"] == "You are a helpful assistant."
        assert result == {"output": "You are a helpful assistant."}
        mock_log.assert_called()

    def test_evaluate_condition_equal(self):
        """Test simple condition evaluation."""
        result = self.executor._evaluate_condition("var==value", {"var": "value"})
        assert result is True

        result = self.executor._evaluate_condition("var==diff", {"var": "value"})
        assert result is False

    def test_evaluate_condition_variable_only(self):
        """Test condition evaluation with non-existent variable."""
        result = self.executor._evaluate_condition("missing==value", {})
        assert result is False

    def test_evaluate_condition_invalid_syntax(self):
        """Test condition evaluation with invalid syntax."""
        result = self.executor._evaluate_condition("invalid condition", {"var": "value"})
        assert result is True  # Default fallback

    def test_should_follow_edge_conditional_true(self):
        """Test edge following for conditional node."""
        edge = Edge(id="e1", source="cond", target="target", target_handle="true")

        node = NodeData(id="cond", type="conditional", position={"x": 0, "y": 0}, data={})
        context = ExecutionContext(variables={"condition_result": True}, output=[], logs=[])

        result = self.executor._should_follow_edge(edge, node, context)
        assert result is True

    def test_should_follow_edge_conditional_false(self):
        """Test edge following for conditional node false path."""
        edge = Edge(id="e1", source="cond", target="target", target_handle="false")

        node = NodeData(id="cond", type="conditional", position={"x": 0, "y": 0}, data={})
        context = ExecutionContext(variables={"condition_result": False}, output=[], logs=[])

        result = self.executor._should_follow_edge(edge, node, context)
        assert result is True

    def test_should_follow_edge_conditional_wrong_handle(self):
        """Test edge following for conditional node wrong handle."""
        edge = Edge(id="e1", source="cond", target="target", target_handle="other")

        node = NodeData(id="cond", type="conditional", position={"x": 0, "y": 0}, data={})
        context = ExecutionContext(variables={"condition_result": True}, output=[], logs=[])

        result = self.executor._should_follow_edge(edge, node, context)
        assert result is True  # Default case

    def test_should_follow_edge_non_conditional(self):
        """Test edge following for non-conditional nodes."""
        edge = Edge(id="e1", source="other", target="target")

        node = NodeData(id="other", type="logic", position={"x": 0, "y": 0}, data={})
        context = ExecutionContext(variables={}, output=[], logs=[])

        result = self.executor._should_follow_edge(edge, node, context)
        assert result is True  # Default behavior

    def test_log_event_creation(self, mocker):
        """Test logging event creation."""
        context = ExecutionContext(variables={}, output=[], logs=[{}, {}])  # 2 existing logs

        start_time = datetime.now(timezone.utc)

        with patch('backend.circuit_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = start_time
            self.executor._log_event(context, "TEST_EVENT", {"key": "value"}, "WARN")

        assert len(context.logs) == 3
        log_entry = context.logs[-1]
        assert log_entry["timestamp"] == start_time.isoformat()
        assert log_entry["level"] == "WARN"
        assert log_entry["event"] == "TEST_EVENT"
        assert log_entry["details"] == {"key": "value"}
        assert log_entry["node_id"] is None  # No current node