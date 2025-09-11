"""
Circuit Execution Engine for CoolChat

This module handles the execution of circuit workflows, processing block logic,
and managing data flow between connected blocks.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
import random
import math

try:
    from .database import get_db
    from .models import Character, Lorebook, LoreEntry
    from sqlalchemy.orm import Session
except ImportError:
    # For standalone testing
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from database import get_db
    from models import Character, Lorebook, LoreEntry
    from sqlalchemy.orm import Session


class CircuitExecutionError(Exception):
    """Raised when circuit execution fails"""
    pass


class BlockExecutionContext:
    """Context object passed to block execution methods"""

    def __init__(self, db: Session, circuit_data: Dict[str, Any], execution_id: str):
        self.db = db
        self.circuit_data = circuit_data
        self.execution_id = execution_id
        self.block_outputs: Dict[str, Any] = {}
        self.execution_log: List[str] = []
        self.errors: List[str] = []

    def set_block_output(self, block_id: str, output_name: str, value: Any):
        """Store output value from a block"""
        if block_id not in self.block_outputs:
            self.block_outputs[block_id] = {}
        self.block_outputs[block_id][output_name] = value
        self.execution_log.append(f"Block {block_id} output {output_name}: {str(value)[:100]}...")

    def get_block_output(self, block_id: str, output_name: str) -> Any:
        """Retrieve output value from a block"""
        return self.block_outputs.get(block_id, {}).get(output_name)

    def get_input_value(self, block_id: str, input_name: str) -> Any:
        """Get input value for a block (from connected outputs or block data)"""
        nodes = self.circuit_data.get('nodes', [])
        connections = self.circuit_data.get('edges', [])

        # Find the block data
        block = None
        if isinstance(nodes, list):
            block = next((node for node in nodes if node.get('id') == block_id), {})
        else:
            block = nodes.get(block_id, {})

        # Find connection to this input
        for conn in connections:
            if conn.get('target') == block_id and conn.get('targetHandle') == f'input-{input_name}':
                source_block_id = conn.get('source')
                source_output_name = conn.get('sourceHandle', '').replace('output-', '')
                return self.get_block_output(source_block_id, source_output_name)

        # No connection found, return default value from block data
        return block.get('data', {}).get(input_name)

    def log(self, message: str):
        """Add log message"""
        self.execution_log.append(f"{datetime.now().isoformat()}: {message}")

    def error(self, message: str):
        """Add error message"""
        self.errors.append(message)
        self.log(f"ERROR: {message}")


class CircuitExecutor:
    """Main circuit execution engine"""

    def __init__(self):
        self.block_processors = {
            # Basic blocks
            'basic_text': self._process_basic_text,
            'boolean': self._process_boolean,
            'switch': self._process_switch,

            # Data source blocks
            'format_persona': self._process_format_persona,
            'character_current': self._process_character_current,
            'character_description': self._process_character_description,
            'chat_history': self._process_chat_history,

            # Variables and templates
            'variables_substitution': self._process_variables_substitution,
            'template_text_formatter': self._process_template_text_formatter,
            'template_system_prompt': self._process_template_system_prompt,

            # Logic blocks
            'logic_counter': self._process_logic_counter,
            'logic_random_number': self._process_logic_random_number,
            'logic_random_choice': self._process_logic_random_choice,
            'logic_conditional': self._process_logic_conditional,
            'logic_comparator': self._process_logic_comparator,

            # Data manipulation
            'data_string_concat': self._process_data_string_concat,
            'data_string_split': self._process_data_string_split,
            'data_string_replace': self._process_data_string_replace,
            'data_math_operation': self._process_data_math_operation,
            'data_array_filter': self._process_data_array_filter,

            # Time and context
            'time_current': self._process_time_current,
            'time_formatter': self._process_time_formatter,
            'context_user_message': self._process_context_user_message,
            'context_ai_response': self._process_context_ai_response,

            # Memory blocks
            'memory_recent_messages': self._process_memory_recent_messages,
            'memory_search': self._process_memory_search,

            # AI integration
            'ai_command': self._process_ai_command,
            'ai_model_selector': self._process_ai_model_selector,
            'ai_temperature': self._process_ai_temperature,
            'ai_max_context_tokens': self._process_ai_max_context_tokens,

            # Endpoints
            'endpoint_chat_reply': self._process_endpoint_chat_reply,
            'endpoint_image_generator': self._process_endpoint_image_generator,
        }

    async def execute_circuit(self, circuit_data: Dict[str, Any], context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a circuit and return results

        Args:
            circuit_data: Circuit definition with nodes and edges
            context_data: Additional context (user_id, character_id, chat_history, etc.)

        Returns:
            Execution results including outputs and logs
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        db = next(get_db())
        try:
            ctx = BlockExecutionContext(db, circuit_data, execution_id)

            # Set context data
            if context_data:
                ctx.context_data = context_data
            else:
                ctx.context_data = {}

            ctx.log("Starting circuit execution")

            try:
                # Execute blocks in topological order
                await self._execute_blocks_topological(ctx)

                # Collect endpoint outputs
                endpoint_outputs = self._collect_endpoint_outputs(ctx)

                ctx.log("Circuit execution completed")

                return {
                    'execution_id': execution_id,
                    'success': True,
                    'outputs': endpoint_outputs,
                    'logs': ctx.execution_log,
                    'errors': ctx.errors,
                    'block_outputs': ctx.block_outputs
                }

            except Exception as e:
                ctx.error(f"Circuit execution failed: {str(e)}")
                return {
                    'execution_id': execution_id,
                    'success': False,
                    'outputs': {},
                    'logs': ctx.execution_log,
                    'errors': ctx.errors,
                    'block_outputs': ctx.block_outputs
                }
        finally:
            db.close()

    async def _execute_blocks_topological(self, ctx: BlockExecutionContext):
        """Execute blocks in topological order based on connections"""
        nodes = ctx.circuit_data.get('nodes', [])
        edges = ctx.circuit_data.get('edges', [])

        # Build adjacency list
        graph = {node['id']: [] for node in nodes}
        in_degree = {node['id']: 0 for node in nodes}

        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source in graph and target in in_degree:
                graph[source].append(target)
                in_degree[target] += 1

        # Find nodes with no incoming edges (start nodes)
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]

        executed = set()

        while queue:
            current_node_id = queue.pop(0)
            if current_node_id in executed:
                continue

            # Execute block
            await self._execute_block(ctx, current_node_id)
            executed.add(current_node_id)

            # Decrease in-degree of neighbors
            for neighbor in graph[current_node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles (nodes with remaining in-degree > 0)
        remaining = [node_id for node_id, degree in in_degree.items() if degree > 0]
        if remaining:
            ctx.error(f"Circular dependencies detected in nodes: {remaining}")

    async def _execute_block(self, ctx: BlockExecutionContext, block_id: str):
        """Execute a single block"""
        nodes = ctx.circuit_data.get('nodes', [])
        block_data = None

        if isinstance(nodes, list):
            block_data = next((node for node in nodes if node.get('id') == block_id), None)
        else:
            block_data = nodes.get(block_id)

        if not block_data:
            ctx.error(f"Block {block_id} not found")
            return

        block_type = block_data.get('type', '')
        processor = self.block_processors.get(block_type)

        if not processor:
            ctx.error(f"No processor found for block type: {block_type}")
            return

        try:
            ctx.log(f"Executing block {block_id} of type {block_type}")
            await processor(ctx, block_id, block_data)
        except Exception as e:
            ctx.error(f"Block {block_id} execution failed: {str(e)}")

    def _collect_endpoint_outputs(self, ctx: BlockExecutionContext) -> Dict[str, Any]:
        """Collect outputs from endpoint blocks"""
        outputs = {}
        nodes = ctx.circuit_data.get('nodes', [])

        for node in nodes:
            if node.get('type', '').startswith('endpoint_'):
                block_id = node['id']
                block_outputs = ctx.block_outputs.get(block_id, {})
                if block_outputs:
                    outputs[node['type']] = block_outputs

        return outputs

    # Block processors implementation

    async def _process_basic_text(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process basic text block"""
        text_value = ctx.get_input_value(block_id, 'text') or block_data.get('data', {}).get('text', '')
        ctx.set_block_output(block_id, 'output', text_value)

    async def _process_boolean(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process boolean comparison block"""
        input1 = ctx.get_input_value(block_id, 'input1')
        input2 = ctx.get_input_value(block_id, 'input2')

        equal = input1 == input2
        ctx.set_block_output(block_id, 'true', input1 if equal else None)
        ctx.set_block_output(block_id, 'false', input1 if not equal else None)

    async def _process_switch(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process switch block"""
        input_value = ctx.get_input_value(block_id, 'input')
        signal = ctx.get_input_value(block_id, 'signal')

        output = input_value if signal is not None else None
        ctx.set_block_output(block_id, 'output', output)

    async def _process_format_persona(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process format persona block"""
        # Get user persona from context or config
        persona = ctx.context_data.get('user_persona', {})
        ctx.set_block_output(block_id, 'name', persona.get('name', ''))
        ctx.set_block_output(block_id, 'description', persona.get('description', ''))

    async def _process_character_current(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process current character block"""
        char_id = ctx.context_data.get('current_character_id')
        char_name = ctx.context_data.get('current_character_name', '')

        ctx.set_block_output(block_id, 'character', char_name)
        ctx.set_block_output(block_id, 'character_id', char_id)

    async def _process_character_description(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process character description block"""
        char_id = ctx.get_input_value(block_id, 'character_id')

        if char_id:
            character = ctx.db.query(Character).filter(Character.id == char_id).first()
            description = character.description if character else ''
        else:
            description = ''

        ctx.set_block_output(block_id, 'description', description)

    async def _process_chat_history(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process chat history block"""
        messages_limit = ctx.get_input_value(block_id, 'messages') or ctx.context_data.get('messages_limit')
        chat_history = ctx.context_data.get('chat_history', [])

        if messages_limit and isinstance(messages_limit, int):
            limited_history = chat_history[-messages_limit:]
        else:
            limited_history = chat_history

        # Format as string
        formatted_history = '\n'.join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in limited_history
        ])

        ctx.set_block_output(block_id, 'chathistory', formatted_history)

    async def _process_variables_substitution(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process variables substitution block"""
        template = ctx.get_input_value(block_id, 'template_text') or ''
        variables = ctx.get_input_value(block_id, 'variables_map') or {}

        # Perform {{key}} substitution
        result = template
        for key, value in variables.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))

        ctx.set_block_output(block_id, 'processed_text', result)

    async def _process_template_text_formatter(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process text formatter template block"""
        inputs = {}
        for input_name in ['input1', 'input2', 'input3', 'input4', 'input5']:
            value = ctx.get_input_value(block_id, input_name)
            if value is not None:
                inputs[input_name] = value

        template = block_data.get('data', {}).get('template', '')
        formatted = template.format(**inputs)

        ctx.set_block_output(block_id, 'formatted_text', formatted)

    async def _process_template_system_prompt(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process system prompt template block"""
        prompt_type = block_data.get('data', {}).get('prompt_type', 'main')

        # Get system prompt templates from context
        templates = ctx.context_data.get('system_prompts', {})

        system_prompt = templates.get(prompt_type, '')
        ctx.set_block_output(block_id, 'system_prompt', system_prompt)

    async def _process_logic_counter(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process counter block"""
        action = ctx.get_input_value(block_id, 'action') or 'increment'
        reset_trigger = ctx.get_input_value(block_id, 'reset')

        # Get current count (would need persistent storage in real implementation)
        current_count = ctx.context_data.get('counters', {}).get(block_id, 0)

        if reset_trigger:
            current_count = 0
        elif action == 'increment':
            current_count += 1
        elif action == 'decrement':
            current_count -= 1

        ctx.set_block_output(block_id, 'count', current_count)

    async def _process_logic_random_number(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process random number block"""
        min_val = ctx.get_input_value(block_id, 'min') or 0
        max_val = ctx.get_input_value(block_id, 'max') or 100

        random_num = random.randint(int(min_val), int(max_val))
        ctx.set_block_output(block_id, 'random_number', random_num)

    async def _process_logic_random_choice(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process random choice block"""
        choices = ctx.get_input_value(block_id, 'choices') or []

        if choices and isinstance(choices, list):
            choice = random.choice(choices)
            ctx.set_block_output(block_id, 'selected_choice', choice)
        else:
            ctx.set_block_output(block_id, 'selected_choice', None)

    async def _process_logic_conditional(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process conditional block"""
        condition = ctx.get_input_value(block_id, 'condition')
        true_value = ctx.get_input_value(block_id, 'true_value')
        false_value = ctx.get_input_value(block_id, 'false_value')

        result = true_value if condition else false_value
        ctx.set_block_output(block_id, 'result', result)

    async def _process_logic_comparator(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process comparator block"""
        value1 = ctx.get_input_value(block_id, 'value1')
        value2 = ctx.get_input_value(block_id, 'value2')
        operation = ctx.get_input_value(block_id, 'operation') or '=='

        try:
            if operation == '==':
                result = value1 == value2
            elif operation == '!=':
                result = value1 != value2
            elif operation == '>':
                result = float(value1 or 0) > float(value2 or 0)
            elif operation == '<':
                result = float(value1 or 0) < float(value2 or 0)
            elif operation == '>=':
                result = float(value1 or 0) >= float(value2 or 0)
            elif operation == '<=':
                result = float(value1 or 0) <= float(value2 or 0)
            else:
                result = False
        except (ValueError, TypeError):
            result = False

        ctx.set_block_output(block_id, 'result', result)

    async def _process_data_string_concat(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process string concatenation block"""
        strings = []
        for i in range(1, 6):  # Support up to 5 inputs
            value = ctx.get_input_value(block_id, f'input{i}')
            if value is not None:
                strings.append(str(value))

        separator = ctx.get_input_value(block_id, 'separator') or ''
        result = separator.join(strings)

        ctx.set_block_output(block_id, 'result', result)

    async def _process_data_string_split(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process string split block"""
        input_string = ctx.get_input_value(block_id, 'input') or ''
        separator = ctx.get_input_value(block_id, 'separator') or ' '

        result = str(input_string).split(separator)
        ctx.set_block_output(block_id, 'result', result)

    async def _process_data_string_replace(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process string replace block"""
        input_string = ctx.get_input_value(block_id, 'input') or ''
        old_value = ctx.get_input_value(block_id, 'old') or ''
        new_value = ctx.get_input_value(block_id, 'new') or ''

        result = str(input_string).replace(str(old_value), str(new_value))
        ctx.set_block_output(block_id, 'result', result)

    async def _process_data_math_operation(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process math operation block"""
        value1 = ctx.get_input_value(block_id, 'value1') or 0
        value2 = ctx.get_input_value(block_id, 'value2') or 0
        operation = ctx.get_input_value(block_id, 'operation') or 'add'

        try:
            v1 = float(value1)
            v2 = float(value2)

            if operation == 'add':
                result = v1 + v2
            elif operation == 'subtract':
                result = v1 - v2
            elif operation == 'multiply':
                result = v1 * v2
            elif operation == 'divide':
                result = v1 / v2 if v2 != 0 else 0
            elif operation == 'power':
                result = v1 ** v2
            else:
                result = 0

            ctx.set_block_output(block_id, 'result', result)
        except (ValueError, TypeError):
            ctx.set_block_output(block_id, 'result', 0)

    async def _process_data_array_filter(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process array filter block"""
        input_array = ctx.get_input_value(block_id, 'input') or []
        filter_condition = ctx.get_input_value(block_id, 'condition')

        if isinstance(input_array, list):
            if filter_condition == 'not_empty':
                result = [item for item in input_array if item]
            elif filter_condition == 'unique':
                result = list(set(input_array))
            else:
                result = input_array
        else:
            result = []

        ctx.set_block_output(block_id, 'result', result)

    async def _process_time_current(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process current time block"""
        now = datetime.now()
        ctx.set_block_output(block_id, 'timestamp', now.isoformat())
        ctx.set_block_output(block_id, 'date', now.date().isoformat())
        ctx.set_block_output(block_id, 'time', now.time().isoformat())

    async def _process_time_formatter(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process time formatter block"""
        timestamp = ctx.get_input_value(block_id, 'timestamp')
        format_pattern = ctx.get_input_value(block_id, 'format') or '%Y-%m-%d %H:%M:%S'

        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.now()

            formatted = dt.strftime(format_pattern)
            ctx.set_block_output(block_id, 'formatted_time', formatted)
        except Exception as e:
            ctx.error(f"Time formatting failed: {str(e)}")
            ctx.set_block_output(block_id, 'formatted_time', str(timestamp))

    async def _process_context_user_message(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process user message context block"""
        user_message = ctx.context_data.get('user_message', '')
        ctx.set_block_output(block_id, 'message', user_message)

    async def _process_context_ai_response(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process AI response context block"""
        ai_response = ctx.context_data.get('ai_response', '')
        ctx.set_block_output(block_id, 'response', ai_response)

    async def _process_memory_recent_messages(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process recent messages memory block"""
        limit = ctx.get_input_value(block_id, 'limit') or 10
        role_filter = ctx.get_input_value(block_id, 'role_filter')

        messages = ctx.context_data.get('chat_history', [])

        if role_filter:
            filtered_messages = [msg for msg in messages if msg.get('role') == role_filter]
        else:
            filtered_messages = messages

        recent_messages = filtered_messages[-int(limit):] if limit else filtered_messages
        ctx.set_block_output(block_id, 'messages', recent_messages)

    async def _process_memory_search(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process memory search block"""
        query = ctx.get_input_value(block_id, 'query') or ''
        messages = ctx.context_data.get('chat_history', [])

        matching_messages = []
        for msg in messages:
            content = msg.get('content', '')
            if query.lower() in content.lower():
                matching_messages.append(msg)

        ctx.set_block_output(block_id, 'matching_messages', matching_messages)

    async def _process_ai_command(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process AI command block"""
        text_input = ctx.get_input_value(block_id, 'textinput') or ''
        prompt = ctx.get_input_value(block_id, 'promptinput') or ''

        # This would integrate with the actual AI service
        # For now, return a placeholder response
        ai_response = f"AI Response to: {text_input} with prompt: {prompt}"

        ctx.set_block_output(block_id, 'output', ai_response)

    async def _process_ai_model_selector(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process AI model selector block"""
        selected_model = ctx.get_input_value(block_id, 'model') or ctx.context_data.get('default_model', 'gpt-3.5-turbo')
        ctx.set_block_output(block_id, 'selected_model', selected_model)

    async def _process_ai_temperature(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process AI temperature block"""
        temperature = ctx.get_input_value(block_id, 'temperature') or 0.7
        ctx.set_block_output(block_id, 'temperature_setting', float(temperature))

    async def _process_ai_max_context_tokens(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process AI max context tokens block"""
        max_tokens = ctx.context_data.get('max_context_tokens', 4096)  # Default to 4096 if not set
        ctx.set_block_output(block_id, 'max_context_tokens', int(max_tokens))

    async def _process_endpoint_chat_reply(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process chat reply endpoint block"""
        prompt = ctx.get_input_value(block_id, 'prompt') or ''

        # This would send the prompt to the AI and get a response
        # For now, just log that the endpoint was triggered
        ctx.log(f"Chat reply endpoint triggered with prompt: {prompt[:100]}...")

        # End-of-line endpoint has no outputs

    async def _process_endpoint_image_generator(self, ctx: BlockExecutionContext, block_id: str, block_data: Dict[str, Any]):
        """Process image generator endpoint block"""
        prompt = ctx.get_input_value(block_id, 'prompt') or ''

        # This would trigger image generation
        # For now, just log that the endpoint was triggered
        ctx.log(f"Image generator endpoint triggered with prompt: {prompt[:50]}...")

        # End-of-line endpoint has no outputs


# Global executor instance
circuit_executor = CircuitExecutor()


async def execute_circuit(circuit_data: Dict[str, Any], context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to execute a circuit"""
    return await circuit_executor.execute_circuit(circuit_data, context_data)