#!/usr/bin/env python3
"""
Test script for circuit execution engine
"""
import asyncio
import json
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_executor import execute_circuit


async def test_basic_circuit():
    """Test a basic circuit with text input and boolean logic"""

    # Create a simple circuit with basic blocks
    circuit_data = {
        "nodes": [
            {
                "id": "text1",
                "type": "basic_text",
                "data": {
                    "label": "Basic Text Block",
                    "type": "basic_text",
                    "text": "Hello World"
                }
            },
            {
                "id": "bool1",
                "type": "boolean",
                "data": {
                    "label": "Boolean Block",
                    "type": "boolean"
                }
            }
        ],
        "edges": [
            {
                "source": "text1",
                "sourceHandle": "output",
                "target": "bool1",
                "targetHandle": "input1"
            },
            {
                "source": "text1",
                "sourceHandle": "output",
                "target": "bool1",
                "targetHandle": "input2"
            }
        ]
    }

    print("Testing basic circuit execution...")
    result = await execute_circuit(circuit_data)

    print(f"Execution ID: {result['execution_id']}")
    print(f"Success: {result['success']}")
    print(f"Outputs: {json.dumps(result['outputs'], indent=2)}")
    print(f"Logs: {result['logs']}")
    print(f"Errors: {result['errors']}")
    print()


async def test_template_circuit():
    """Test a circuit with variable substitution"""

    circuit_data = {
        "nodes": [
            {
                "id": "vars1",
                "type": "variables_substitution",
                "data": {
                    "label": "Variables Substitution",
                    "type": "variables_substitution"
                }
            }
        ],
        "edges": []
    }

    context_data = {
        "variables": {
            "name": "Alice",
            "age": "25"
        }
    }

    print("Testing template circuit with variables...")
    result = await execute_circuit(circuit_data, context_data)

    print(f"Execution ID: {result['execution_id']}")
    print(f"Success: {result['success']}")
    print(f"Outputs: {json.dumps(result['outputs'], indent=2)}")
    print(f"Logs: {result['logs']}")
    print()


async def test_logic_circuit():
    """Test a circuit with logic operations"""

    circuit_data = {
        "nodes": [
            {
                "id": "counter1",
                "type": "logic_counter",
                "data": {
                    "label": "Counter Block",
                    "type": "logic_counter",
                    "action": "increment"
                }
            },
            {
                "id": "random1",
                "type": "logic_random_number",
                "data": {
                    "label": "Random Number",
                    "type": "logic_random_number",
                    "min": 1,
                    "max": 10
                }
            }
        ],
        "edges": []
    }

    print("Testing logic circuit...")
    result = await execute_circuit(circuit_data)

    print(f"Execution ID: {result['execution_id']}")
    print(f"Success: {result['success']}")
    print(f"Outputs: {json.dumps(result['outputs'], indent=2)}")
    print(f"Logs: {result['logs']}")
    print()


async def test_endpoint_circuit():
    """Test a circuit with endpoint blocks"""

    circuit_data = {
        "nodes": [
            {
                "id": "endpoint1",
                "type": "endpoint_chat_reply",
                "data": {
                    "label": "Chat Reply Endpoint",
                    "type": "endpoint_chat_reply"
                }
            }
        ],
        "edges": []
    }

    context_data = {
        "user_message": "Hello, how are you?",
        "chat_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    }

    print("Testing endpoint circuit...")
    result = await execute_circuit(circuit_data, context_data)

    print(f"Execution ID: {result['execution_id']}")
    print(f"Success: {result['success']}")
    print(f"Outputs: {json.dumps(result['outputs'], indent=2)}")
    print(f"Logs: {result['logs']}")
    print()


async def main():
    """Run all circuit tests"""
    print("🧪 Starting Circuit Execution Tests")
    print("=" * 50)

    try:
        await test_basic_circuit()
        await test_template_circuit()
        await test_logic_circuit()
        await test_endpoint_circuit()

        print("✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())