import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useCircuitStore, Circuit } from '../../stores/circuitStore';


import { useConfigStore } from '../../stores/configStore';
import { useDataStore } from '../../stores/dataStore';
import { useLorebookStore } from '../../stores/lorebookStore';
import ReactFlow, { Node, Edge, addEdge, Connection, useNodesState, useEdgesState, Controls, MiniMap, Handle, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import './CircuitEditor.css';

// Block connector configurations
const blockConfigs = {
  // Basic blocks
  basic_text: {     // Outputs whatever string is entered into this block's settings
    inputs: [],
    outputs: ['output'],
    label: 'Basic Text'
  },
  boolean: {        // If input1 = input2 this will output input1 from the true output. Otherwise the false output will output input1
    inputs: ['input1', 'input2'],
    outputs: ['true', 'false'],
    label: 'Boolean Compare'
  },
  switch: {         // If signal input is not null the output will echo the input
    inputs: ['input', 'signal'],
    outputs: ['output'],
    label: 'Switch'
  },

  // Data source blocks
  format_persona: { // Outputs the Persona Username from name and Description from description
    inputs: [],
    outputs: ['name', 'description'],
    label: 'Format: Persona'
  },
  character_current: {  // Outputs the currently active character's name from character and numerical character id from character_id
    inputs: [],
    outputs: ['character', 'character_id'],
    label: 'Character: Current'
  },
  character_description: {    // Will output a JSON object of all character descriptions if there is no input. If character_id receives numerical input description will output the character desciption that corresponds with that character_id
    inputs: ['character_id'],
    outputs: ['description'],
    label: 'Character: Description'
  },
  chat_history: {    // Outputs the entire active chat history from chathistory unless messages receives a numerical input then chathistory will output the x most recent messages where x is the numerical input received.
    inputs: ['messages'],
    outputs: ['chathistory'],
    label: 'Chat: History'
  },

  // Variables and templates
  variables_substitution: {
    inputs: ['template_text', 'variables_map'],
    outputs: ['processed_text'],
    label: 'Variables: Substitution'
  },
  template_text_formatter: {
    inputs: ['input1', 'input2', 'input3', 'input4', 'input5'],
    outputs: ['formatted_text'],
    label: 'Template: Text Formatter'
  },
  template_system_prompt: {
    inputs: [],
    outputs: ['system_prompt'],
    label: 'Template: System Prompt'
  },

  // Logic blocks
  logic_counter: {    // Everytime this block receives an input on action it will iterate the number being output on count (starting on 0). When this receives any input on reset it resets the count to 0
    inputs: ['action', 'reset'],
    outputs: ['count'],
    label: 'Logic: Counter'
  },
  logic_random_number: {    // Outputs a random number between 0 and 256 unless min and max are each receiving numerical input then will output a random number between those two numbers
    inputs: ['min', 'max'],
    outputs: ['random_number'],
    label: 'Logic: Random Number'
  },
  logic_random_choice: {    // Will output one of the 5 choice inputs, while ignoring empty inputs. Will choose a new choice at random whenever it receives any input on reset.
    inputs: ['choice1', 'choice2', 'choice3', 'choice4', 'choice5', 'reset'],
    outputs: ['selected_choice'],
    label: 'Logic: Random Choice'
  },
  logic_conditional: {
    inputs: ['condition', 'true_value', 'false_value'],
    outputs: ['result'],
    label: 'Logic: Conditional'
  },
  logic_comparator: {       // Logic comparator accepts comparison operators ==, !=, <, >, <=, >= and compares value1 and value2, outputting the boolean result
    inputs: ['value1', 'value2', 'operation'],
    outputs: ['result'],
    label: 'Logic: Comparator'
  },

  // Data manipulation
  data_string_concat: {
    inputs: ['input1', 'input2', 'input3', 'input4', 'input5', 'separator'],
    outputs: ['result'],
    label: 'Data: String Concat'
  },
  data_string_split: {
    inputs: ['input', 'separator'],
    outputs: ['result'],
    label: 'Data: String Split'
  },
  data_string_replace: {
    inputs: ['input', 'old', 'new'],
    outputs: ['result'],
    label: 'Data: String Replace'
  },
  data_math_operation: {
    inputs: ['value1', 'value2', 'operation'],
    outputs: ['result'],
    label: 'Data: Math Operation'
  },
  data_array_filter: {
    inputs: ['input', 'condition'],
    outputs: ['result'],
    label: 'Data: Array Filter'
  },

  // Time and context
  time_current: {
    inputs: [],
    outputs: ['timestamp', 'date', 'time'],
    label: 'Time: Current'
  },
  time_formatter: {
    inputs: ['timestamp', 'format'],
    outputs: ['formatted_time'],
    label: 'Time: Formatter'
  },
  context_user_message: {     // Outputs the most recent user message when receiving no input. When receiving numerical input in amount output that many of most recent user messages.
    inputs: ['amount'],
    outputs: ['message'],
    label: 'Context: User Message'
  },
  context_ai_response: {      // Outputs the most recent ai reply when receiving no input. When receiving numerical input in amount output that many of most recent ai replies.
    inputs: [],
    outputs: ['response'],
    label: 'Context: AI Response'
  },

  // Memory blocks
  memory_recent_messages: {
    inputs: ['limit', 'role_filter'],
    outputs: ['messages'],
    label: 'Memory: Recent Messages'
  },
  memory_search: {
    inputs: ['query'],
    outputs: ['matching_messages'],
    label: 'Memory: Search'
  },

  // AI integration
  ai_command: {       // Accepts a string in textinput and sends that to the AI preceded by promptinput. When the AI replies that is output from output
    inputs: ['textinput', 'promptinput'],
    outputs: ['output'],
    label: 'AI: Command'
  },
  ai_model_selector: {    // Outputs the name of the currently selected AI model from selected_model and the provider from provider
    inputs: [],
    outputs: ['selected_model', 'provider'],
    label: 'AI: Model Selector'
  },
  ai_temperature: {       // Outputs the currently selected temperature from the Connection tab
    inputs: [],
    outputs: ['temperature_setting'],
    label: 'AI: Temperature'
  },
  ai_max_context_tokens: {    // Outputs the currently selected max context tokens from the Connection tab
    inputs: [],
    outputs: ['max_context_tokens'],
    label: 'AI: Max Context Tokens'
  },

  // Endpoints
  endpoint_chat_reply: {    // This is the primary chat function and is triggered everytime the user sends a message to the AI in the chat. The circuit ending with this endpoint will output the result to the AI to reply in chat.
    inputs: ['prompt'],
    outputs: [],
    label: 'Endpoint: Chat Reply'
  },
  endpoint_image_generator: {   // The prompt fed into this endpoint is what will be sent to the AI whenever the image generator tool is called (either via the AI using tool calling or the user clicking the button)
    inputs: ['prompt'],
    outputs: [],
    label: 'Endpoint: Image Generator'
  },

  // Legacy blocks (keeping for backward compatibility)
  logic: {
    inputs: ['input1'],
    outputs: ['output'],
    label: 'Logic Block'
  },
  content: {
    inputs: ['text', 'source'],
    outputs: ['result'],
    label: 'Content Block'
  },
  flow: {
    inputs: ['trigger'],
    outputs: ['next', 'branched'],
    label: 'Flow Block'
  },
  integration: {
    inputs: ['request', 'params'],
    outputs: ['response', 'success', 'error'],
    label: 'Integration Block'
  },
  // System Prompt Content Blocks
  system_main: {
    inputs: ['character_data'],
    outputs: ['main_prompt'],
    label: 'System: Main Template'
  },
  system_tool_call: {
    inputs: ['tools_data', 'character_data'],
    outputs: ['tool_instructions'],
    label: 'System: Tool Call'
  },
  system_lore_suggest: {
    inputs: ['lorebook_context'],
    outputs: ['lore_suggest_prompt'],
    label: 'System: Lore Suggest'
  },
  system_image_summary: {
    inputs: ['scene_data', 'character_data'],
    outputs: ['image_summary_prompt'],
    label: 'System: Image Summary'
  },
  // Personalized Format Template Blocks
  format_tools: {
    inputs: ['tools_config'],
    outputs: ['tools_formatted'],
    label: 'Format: Tool Descriptions'
  },
  format_lore_injection: {
    inputs: ['lore_entries'],
    outputs: ['lore_formatted'],
    label: 'Format: Lore Injection'
  },
  // Character-based Prompt Blocks
  char_system_prompt: {
    inputs: ['character_settings'],
    outputs: ['system_preprompt'],
    label: 'Character: System Prompt'
  },
  char_personality: {
    inputs: ['character_data'],
    outputs: ['personality_text'],
    label: 'Character: Personality'
  },
  char_scenario: {
    inputs: ['character_data', 'scenario_data'],
    outputs: ['scenario_text'],
    label: 'Character: Scenario'
  },
  char_first_message: {
    inputs: ['character_data', 'greetings'],
    outputs: ['first_message_text'],
    label: 'Character: First Message'
  },
  // Tool Message Blocks
  tool_image_request: {
    inputs: ['prompt_text', 'generation_params'],
    outputs: ['tool_call_json'],
    label: 'Tool: Image Request'
  },
  tool_phone_url: {
    inputs: ['phone_number', 'url_params'],
    outputs: ['tool_call_json'],
    label: 'Tool: Phone URL'
  },
  tool_lore_suggestions: {
    inputs: ['suggestions_array', 'validation_params'],
    outputs: ['tool_call_json'],
    label: 'Tool: Lore Suggestions'
  },
  // Lorebook Content Blocks
  lorebook_content: {
    inputs: ['keywords', 'content_text', 'trigger_logic'],
    outputs: ['lore_entry'],
    label: 'Lorebook: Content Block'
  },
  // Dynamic Active Lore Blocks
  lore_active_display: {
    inputs: ['active_lore_entries'],
    outputs: ['formatted_lore_display'],
    label: 'Lore: Active Display'
  },
  lore_title_injection: {
    inputs: ['active_lore_entries', 'title_template'],
    outputs: ['titled_lore_block'],
    label: 'Lore: Active Title'
  }
};

// Block extended configurations for properties panel
const blockExtendedConfigs: Record<string, {
  connectorTypes?: { inputs: Record<string, string>, outputs: Record<string, string> };
  configuration?: Array<{ name: string; type: string; description?: string }>;
  metadata?: Array<{ label: string; value: string; description?: string }>;
}> = {
  // System Prompt Blocks
  system_main: {
    connectorTypes: { inputs: { character_data: 'JSON' }, outputs: { main_prompt: 'string' } },
    configuration: [
      { name: 'Template Source', type: 'select', description: 'Full character card or summary' },
      { name: 'System Message Format', type: 'text', description: 'Opening system prompt pattern' }
    ],
    metadata: [
      { label: 'Block Type', value: 'System Prompt Generator', description: 'Generates main system prompt from character data' },
      { label: 'Input Data', value: 'Character Definition', description: 'Full character configuration' }
    ]
  },
  system_tool_call: {
    connectorTypes: { inputs: { tools_data: 'JSON', character_data: 'JSON' }, outputs: { tool_instructions: 'string' } },
    configuration: [{ name: 'Tool Format Schema', type: 'select', description: 'Expected tool call format' }],
    metadata: []
  },
  system_lore_suggest: {
    connectorTypes: { inputs: { lorebook_context: 'JSON' }, outputs: { lore_suggest_prompt: 'string' } },
    configuration: [{ name: 'Lore Selection Strategy', type: 'select', description: 'How to select relevant lore entries' }],
    metadata: []
  },
  system_image_summary: {
    connectorTypes: { inputs: { scene_data: 'JSON', character_data: 'JSON' }, outputs: { image_summary_prompt: 'string' } },
    configuration: [
      { name: 'Image Style Preferences', type: 'text', description: 'Artistic style hints' },
      { name: 'Level of Detail', type: 'select', description: 'Summary depth' }
    ],
    metadata: []
  },
  // Format Template Blocks
  format_persona: {
    connectorTypes: { inputs: { user_persona: 'string' }, outputs: { persona_formatted: 'string' } },
    configuration: [
      { name: 'Format Template', type: 'text', description: 'Variable substitution pattern' },
      { name: 'Variable Delimiters', type: 'select', description: '{{ }} or << >> style' }
    ],
    metadata: []
  },
  format_tools: {
    connectorTypes: { inputs: { tools_config: 'JSON' }, outputs: { tools_formatted: 'string' } },
    configuration: [{ name: 'Tool Documentation Format', type: 'text', description: 'How to format tool descriptions' }],
    metadata: []
  },
  format_lore_injection: {
    connectorTypes: { inputs: { lore_entries: 'array' }, outputs: { lore_formatted: 'string' } },
    configuration: [
      { name: 'Injection Pattern', type: 'text', description: 'How to merge lore entries' },
      { name: 'Separator Style', type: 'select', description: 'Newlines, bullets, or paragraphs' }
    ],
    metadata: []
  },
  // Character-based Prompt Blocks
  char_system_prompt: {
    connectorTypes: { inputs: { character_settings: 'JSON' }, outputs: { system_preprompt: 'string' } },
    configuration: [{ name: 'System Prompt Structure', type: 'text', description: 'Character role and behavior' }],
    metadata: []
  },
  char_personality: {
    connectorTypes: { inputs: { character_data: 'JSON' }, outputs: { personality_text: 'string' } },
    configuration: [{ name: 'Personality Format', type: 'select', description: 'Narrative or list style' }],
    metadata: []
  },
  char_scenario: {
    connectorTypes: { inputs: { character_data: 'JSON', scenario_data: 'string' }, outputs: { scenario_text: 'string' } },
    configuration: [
      { name: 'Scenario Enhancement', type: 'text', description: 'Additional context to add' },
      { name: 'Time Period', type: 'select', description: 'Story setting time' }
    ],
    metadata: []
  },
  char_first_message: {
    connectorTypes: { inputs: { character_data: 'JSON', greetings: 'string' }, outputs: { first_message_text: 'string' } },
    configuration: [
      { name: 'Greeting Style', type: 'select', description: 'Formal, casual, or character-specific' },
      { name: 'Message Length', type: 'select', description: 'Short, medium, or detailed opening' }
    ],
    metadata: []
  },
  // Tool Message Blocks
  tool_image_request: {
    connectorTypes: { inputs: { prompt_text: 'string', generation_params: 'JSON' }, outputs: { tool_call_json: 'JSON' } },
    configuration: [
      { name: 'Image Model', type: 'select', description: 'AI image generation model' },
      { name: 'Output Format', type: 'select', description: 'JSON structure for tool call' }
    ],
    metadata: []
  },
  tool_phone_url: {
    connectorTypes: { inputs: { phone_number: 'string', url_params: 'JSON' }, outputs: { tool_call_json: 'JSON' } },
    configuration: [{ name: 'URL Pattern', type: 'text', description: 'Format for URL construction' }],
    metadata: []
  },
  tool_lore_suggestions: {
    connectorTypes: { inputs: { suggestions_array: 'array', validation_params: 'JSON' }, outputs: { tool_call_json: 'JSON' } },
    configuration: [
      { name: 'Suggestion Limits', type: 'number', description: 'Maximum suggestions to include' },
      { name: 'Validation Rules', type: 'text', description: 'Criteria for valid suggestions' }
    ],
    metadata: []
  },
  // Lorebook Content Blocks
  lorebook_content: {
    connectorTypes: { inputs: { keywords: 'string', content_text: 'string', trigger_logic: 'string' }, outputs: { lore_entry: 'JSON' } },
    configuration: [
      { name: 'Entry Priority', type: 'select', description: 'How to rank this entry' },
      { name: 'Trigger Sensitivity', type: 'select', description: 'Keyword matching strictness' }
    ],
    metadata: []
  },
  // Variables Block
  variables_substitution: {
    connectorTypes: { inputs: { template_text: 'string', variables_map: 'JSON' }, outputs: { processed_text: 'string' } },
    configuration: [
      { name: 'Variable Syntax', type: 'select', description: '{{var}} or ${var} substitution' },
      { name: 'Error Handling', type: 'select', description: 'How to handle missing variables' }
    ],
    metadata: [
      { label: 'Substitution Type', value: 'Key/Value Replacement', description: 'Replaces markers with data values' },
      { label: 'Supported Formats', value: 'JSON Map/Object', description: 'Variables input structure' }
    ]
  },
  // Dynamic Active Lore Blocks
  lore_active_display: {
    connectorTypes: { inputs: { active_lore_entries: 'array' }, outputs: { formatted_lore_display: 'string' } },
    configuration: [
      { name: 'Display Format', type: 'select', description: 'How to present active lore' },
      { name: 'Max Length', type: 'number', description: 'Character limit for display' }
    ],
    metadata: []
  },
  lore_title_injection: {
    connectorTypes: { inputs: { active_lore_entries: 'array', title_template: 'string' }, outputs: { titled_lore_block: 'string' } },
    configuration: [
      { name: 'Title Format', type: 'text', description: 'Prefix pattern for lore entries' },
      { name: 'Sorting Order', type: 'select', description: 'How to order entries' }
    ],
    metadata: []
  }
};

// Block components with dynamic connectors
const BlockNode = ({ data }: any) => {
  const config = blockConfigs[data.type] || { inputs: [], outputs: [], label: 'Unknown Block' };
  const totalConnectors = Math.max(config.inputs.length, config.outputs.length, 1);
  const blockHeight = 80 + (totalConnectors * 20); // Base height + space for connectors

  // Calculate connector spacing
  const getConnectorTop = (index: number, total: number) => {
    const start = 20;
    const spacing = (blockHeight - 40) / Math.max(total - 1, 1);
    return start + (index * spacing);
  };

  return (
    <div
      className={`circuit-block circuit-${data.type}`}
      style={{ height: blockHeight, minHeight: 100 }}
    >
      {/* Input connectors (left side) */}
      {config.inputs.map((inputName, index) => (
        <Handle
          key={`input-${inputName}`}
          id={`input-${inputName}`}
          type="target"
          position={Position.Left}
          className="handle-input"
          style={{
            top: getConnectorTop(index, config.inputs.length) - 6
          }}
          title={`Input: ${inputName}`}
        />
      ))}

      {/* Output connectors (right side) */}
      {config.outputs.map((outputName, index) => (
        <Handle
          key={`output-${outputName}`}
          id={`output-${outputName}`}
          type="source"
          position={Position.Right}
          className="handle-output"
          style={{
            top: getConnectorTop(index, config.outputs.length) - 6
          }}
          title={`Output: ${outputName}`}
        />
      ))}

      {/* Block content */}
      <div className="block-content-flex">
        <span className="block-icon-large">
          {data.icon}
        </span>
        <span className="block-label">
          {config.label}
        </span>
        <span className="block-connector-count">
          {totalConnectors} connections
        </span>
      </div>
    </div>
  );
};

// Helper functions for properties pane
const getBlockDescription = (blockType: string): string => {
  const descriptions: Record<string, string> = {
    // Basic blocks
    basic_text: "Outputs whatever string or number is entered into this block's settings. Can be configured to accept text or numbers only.",
    boolean: "Compares two inputs and outputs to 'true' if they match, otherwise outputs to 'false'.",
    switch: "If signal input is not null the output will echo the input, otherwise outputs nothing.",

    // Data source blocks
    format_persona: "Outputs the currently active user's name and description from their persona settings.",
    character_current: "Outputs the currently active character's name and numerical character ID.",
    character_description: "Outputs character description. If no character_id input provided, returns all character descriptions.",
    chat_history: "Outputs chat history. With messages input, returns the x most recent messages where x is the input value.",

    // Variables and templates
    variables_substitution: "Replaces {{variable}} placeholders in template_text with values from variables_map.",
    template_text_formatter: "Combines up to 5 input strings using a custom template format.",
    template_system_prompt: "Outputs the currently configured system prompt template.",

    // Logic blocks
    logic_counter: "Increments count each time action input is triggered. Resets when reset input is triggered.",
    logic_random_number: "Outputs a random number between min and max inputs (or 0-100 if not specified).",
    logic_random_choice: "Outputs one randomly selected choice from the configured number of available choices.",
    logic_conditional: "Outputs true_value if condition is truthy, otherwise outputs false_value.",
    logic_comparator: "Compares value1 and value2 using the selected comparison operator (==, !=, <, >, >=, <=).",

    // Data manipulation
    data_string_concat: "Concatenates up to 5 input strings with an optional separator.",
    data_string_split: "Splits input string by separator and returns array of parts.",
    data_string_replace: "Replaces occurrences of 'old' substring with 'new' substring in input string.",
    data_math_operation: "Performs mathematical operations (+, -, *, /, ^, %) on value1 and value2.",
    data_array_filter: "Filters array input based on condition ('not_empty' or 'unique').",

    // Time and context
    time_current: "Outputs current timestamp, date, and time information.",
    time_formatter: "Formats timestamp input using specified format pattern.",
    context_user_message: "Outputs the most recent user message, or the last x messages if amount specified.",
    context_ai_response: "Outputs the most recent AI response.",

    // Memory blocks
    memory_recent_messages: "Outputs recent messages from chat history, filtered by role if specified.",
    memory_search: "Searches chat history for messages containing the query string.",

    // AI integration
    ai_command: "Sends textinput to AI with promptinput as system prompt, outputs AI response.",
    ai_model_selector: "Outputs the currently selected AI model name and provider.",
    ai_temperature: "Outputs the currently configured AI temperature setting.",
    ai_max_context_tokens: "Outputs the currently configured maximum context tokens for AI.",

    // Endpoints
    endpoint_chat_reply: "Circuit endpoint that sends prompt to AI for chat response. End-of-line block with no outputs.",
    endpoint_image_generator: "Circuit endpoint that triggers AI image generation from prompt. End-of-line block with no outputs."
  };
  return descriptions[blockType] || "No description available.";
};

const renderBlockSettings = (node: Node, onUpdateNode: (nodeId: string, updates: any) => void): JSX.Element | null => {
  const blockType = node.data.type;
  const blockData = node.data;
  console.log('renderBlockSettings called for node:', node.id, 'data:', blockData);

  switch (blockType) {
    case 'basic_text':
      return (
        <div className="block-settings-content">
          <div className="setting-item">
            <label htmlFor="basic-text-input">Text Content:</label>
            <input
              id="basic-text-input"
              type="text"
              value={blockData.text || ''}
              onChange={(e) => {
                console.log('Text input changed:', e.target.value);
                onUpdateNode(node.id, { text: e.target.value });
              }}
              placeholder="Enter text to output..."
            />
          </div>
          <div className="setting-item">
            <label htmlFor="basic-text-mode">Output Type:</label>
            <select
              id="basic-text-mode"
              value={blockData.outputMode || 'string'}
              onChange={(e) => {
                onUpdateNode(node.id, { outputMode: e.target.value });
              }}
            >
              <option value="string">String (Text)</option>
              <option value="number">Number Only</option>
            </select>
          </div>
        </div>
      );

    case 'logic_comparator':
      return (
        <div className="block-settings-content">
          <div className="setting-item">
            <label htmlFor="comparator-op">Comparison Operator:</label>
            <select
              id="comparator-op"
              value={blockData.operation || '=='}
              onChange={(e) => {
                onUpdateNode(node.id, { operation: e.target.value });
              }}
            >
              <option value="==">Equal</option>
              <option value="!=">Not Equal</option>
              <option value="<">Less Than</option>
              <option value=">">Greater Than</option>
              <option value="<=">Less Than or Equal</option>
              <option value=">=">Greater Than or Equal</option>
            </select>
          </div>
        </div>
      );

    case 'logic_random_choice':
      return (
        <div className="block-settings-content">
          <div className="setting-item">
            <label htmlFor="choice-count">Number of Choices: {blockData.choiceCount || 3}</label>
            <input
              id="choice-count"
              type="range"
              min="2"
              max="10"
              value={blockData.choiceCount || 3}
              onChange={(e) => {
                onUpdateNode(node.id, { choiceCount: parseInt(e.target.value) });
              }}
            />
          </div>
        </div>
      );

    default:
      return <div className="no-settings">No settings available for this block type.</div>;
  }
};

const renderCurrentValues = (node: Node): JSX.Element => {
  const blockType = node.data.type;
  const config = blockConfigs[blockType];

  return (
    <div className="current-values-content">
      {/* Input Values */}
      {config.inputs.length > 0 && (
        <div className="values-section">
          <h6>📥 Input Values</h6>
          {config.inputs.map((inputName, index) => (
            <div key={inputName} className="value-item">
              <span className="value-label">{inputName}:</span>
              <span className="value-display">
                {/* This would show actual input values from connected blocks */}
                <em>Not connected</em>
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Output Values */}
      {config.outputs.length > 0 && (
        <div className="values-section">
          <h6>📤 Output Values</h6>
          {config.outputs.map((outputName, index) => (
            <div key={outputName} className="value-item">
              <span className="value-label">{outputName}:</span>
              <span className="value-display">
                {/* This would show actual output values from execution */}
                <em>Not executed</em>
              </span>
            </div>
          ))}
        </div>
      )}

      {config.inputs.length === 0 && config.outputs.length === 0 && (
        <div className="no-values">This block has no inputs or outputs.</div>
      )}
    </div>
  );
};

const nodeTypes = {
  // Basic blocks
  basic_text: BlockNode,
  boolean: BlockNode,
  switch: BlockNode,

  // Data source blocks
  format_persona: BlockNode,
  character_current: BlockNode,
  character_description: BlockNode,
  chat_history: BlockNode,

  // Variables and templates
  variables_substitution: BlockNode,
  template_text_formatter: BlockNode,
  template_system_prompt: BlockNode,

  // Logic blocks
  logic_counter: BlockNode,
  logic_random_number: BlockNode,
  logic_random_choice: BlockNode,
  logic_conditional: BlockNode,
  logic_comparator: BlockNode,

  // Data manipulation
  data_string_concat: BlockNode,
  data_string_split: BlockNode,
  data_string_replace: BlockNode,
  data_math_operation: BlockNode,
  data_array_filter: BlockNode,

  // Time and context
  time_current: BlockNode,
  time_formatter: BlockNode,
  context_user_message: BlockNode,
  context_ai_response: BlockNode,

  // Memory blocks
  memory_recent_messages: BlockNode,
  memory_search: BlockNode,

  // AI integration
  ai_command: BlockNode,
  ai_model_selector: BlockNode,
  ai_temperature: BlockNode,
  ai_max_context_tokens: BlockNode,

  // Endpoints
  endpoint_chat_reply: BlockNode,
  endpoint_image_generator: BlockNode,

  // Legacy blocks (keeping for backward compatibility)
  logic: BlockNode,
  content: BlockNode,
  flow: BlockNode,
  integration: BlockNode,
  // System Prompt Blocks
  system_main: BlockNode,
  system_tool_call: BlockNode,
  system_lore_suggest: BlockNode,
  system_image_summary: BlockNode,
  // Format Template Blocks
  format_tools: BlockNode,
  format_lore_injection: BlockNode,
  // Character-based Blocks
  char_system_prompt: BlockNode,
  char_personality: BlockNode,
  char_scenario: BlockNode,
  char_first_message: BlockNode,
  // Tool Message Blocks
  tool_image_request: BlockNode,
  tool_phone_url: BlockNode,
  tool_lore_suggestions: BlockNode,
  // Lorebook Content Blocks
  lorebook_content: BlockNode,
  // Dynamic Active Lore Blocks
  lore_active_display: BlockNode,
  lore_title_injection: BlockNode,
};

export const CircuitEditor2: React.FC = () => {
  const circuitStore = useCircuitStore();
  const { userPersona, providers, activeProvider, loadConfig } = useConfigStore();
  const { characters, loadCharacters, lorebooks, findCharacterById } = useDataStore();
  const { loreEntries, selectedLorebook, selectLorebook, fetchLorebooks, refreshLoreEntries } = useLorebookStore();
  const [entryLoading, setEntryLoading] = useState(false);
  const { circuits, current, fetchCircuits, saveCircuit, executeCircuit, executionResult, isExecuting } = useCircuitStore();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', description: '' });
  const [showExecutionResults, setShowExecutionResults] = useState(false);
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);
  const [executionOutputs, setExecutionOutputs] = useState<Record<string, any>>({});
  // Live data states
  const [liveDataLoading, setLiveDataLoading] = useState<{ [key: string]: boolean }>({});
  const [liveDataErrors, setLiveDataErrors] = useState<{ [key: string]: string }>({});
  const [blockData, setBlockData] = useState<{ [key: string]: any }>({});
  const [promptsData, setPromptsData] = useState<{ variables: Record<string, string> } | null>(null);
  const [dataInitialized, setDataInitialized] = useState(false);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  // Height calculation state
  const [containerHeight, setContainerHeight] = useState<number>(400);
  // Force re-render counter for properties panel
  const [propertiesKey, setPropertiesKey] = useState<number>(0);

  // Calculate available height for ReactFlow container
  const calculateAvailableHeight = useCallback(() => {
//    const headerHeight = 310; // Height of the toolbar/header
//    const padding = 16; // Total padding (top + bottom)
//    const availableHeight = window.innerHeight - headerHeight - padding;
      const availableHeight = window.innerHeight * 0.64 //Just make the canvas 64% of the screen 
    return Math.max(availableHeight, 300); // Minimum height of 300px to prevent collapse
  }, []);

  // Initialize and update container height on mount and window resize
  useEffect(() => {
    const updateHeight = () => setContainerHeight(calculateAvailableHeight());

    // Set initial height
    updateHeight();

    // Add resize listener for responsive behavior
    const handleResize = () => updateHeight();
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, [calculateAvailableHeight]);

  useEffect(() => {
    fetchCircuits().catch(err => {
      console.error('Failed to fetch circuits:', err);
    });
  }, [fetchCircuits]);

  const deleteSelectedNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((nodes) => nodes.filter((node) => node.id !== selectedNode.id));
    setEdges((edges) => edges.filter(edge => edge.source !== selectedNode.id && edge.target !== selectedNode.id));
    setSelectedNode(null);
  }, [selectedNode, setNodes, setEdges]);

  useEffect(() => {
    if (circuitStore.current) {
      setNodes((circuitStore.current.data as any).nodes || []);
      setEdges((circuitStore.current.data as any).edges || []);
      setSelectedNode(null);
    }
  }, [circuitStore.current, setNodes, setEdges, setSelectedNode]);

  // Update selectedNode when nodes data changes
  useEffect(() => {
    if (selectedNode) {
      const currentNode = nodes.find(node => node.id === selectedNode.id);
      if (currentNode && currentNode.data !== selectedNode.data) {
        console.log('Updating selectedNode to match current node data');
        setSelectedNode(currentNode);
      }
    }
  }, [nodes, selectedNode, setSelectedNode]);

  // Live data initialization and subscriptions
  useEffect(() => {
    const initializeData = async () => {
      if (dataInitialized) return;

      try {
        setLiveDataLoading(prev => ({ ...prev, config: true, data: true, lorebook: true }));

        // Load configuration data (persona, providers)
        await loadConfig();

        // Load character and lorebook data
        await Promise.all([
          loadCharacters(),
          fetchLorebooks()
        ]);

        // Load prompts.json for variables
        try {
          const response = await fetch('/backend/prompts.json');
          if (response.ok) {
            const prompts = await response.json();
            setPromptsData(prompts);
          }
        } catch (error) {
          console.warn('Failed to load prompts.json:', error);
          setLiveDataErrors(prev => ({ ...prev, prompts: 'Failed to load variables' }));
        }

        setDataInitialized(true);
        setLiveDataLoading(prev => ({ config: false, data: false, lorebook: false }));

      } catch (error) {
        console.error('Failed to initialize live data:', error);
        setLiveDataErrors(prev => ({ ...prev, init: 'Failed to load application data' }));
        setLiveDataLoading(prev => ({ config: false, data: false, lorebook: false }));
      }
    };

    initializeData();
  }, [dataInitialized, loadConfig, loadCharacters, fetchLorebooks]);

  // Refresh function for manual data updates
  const refreshBlockData = useCallback(async (blockType?: string) => {
    try {
      setLiveDataLoading(prev => ({ ...prev, [blockType || 'all']: true }));

      switch (blockType) {
        case 'persona':
        case 'format_persona':
          await loadConfig();
          break;
        case 'tools':
        case 'format_tools':
          await loadConfig();
          break;
        case 'lore':
        case 'format_lore_injection':
          await fetchLorebooks();
          if (selectedLorebook) await refreshLoreEntries();
          break;
        case 'character':
          await loadCharacters();
          break;
        case 'variables':
        case 'variables_substitution':
          try {
            const response = await fetch('/backend/prompts.json');
            if (response.ok) {
              const prompts = await response.json();
              setPromptsData(prompts);
            }
          } catch (error) {
            setLiveDataErrors(prev => ({ ...prev, prompts: 'Failed to reload variables' }));
          }
          break;
        default:
          // Refresh all data
          await loadConfig();
          await Promise.all([
            loadCharacters(),
            fetchLorebooks()
          ]);
          if (selectedLorebook) await refreshLoreEntries();
          break;
      }

      setLiveDataLoading(prev => ({ ...prev, [blockType || 'all']: false }));
    } catch (error) {
      console.error(`Failed to refresh ${blockType || 'all'} data:`, error);
      setLiveDataErrors(prev => ({
        ...prev,
        [blockType || 'all']: `Failed to refresh ${blockType || 'all'} data`
      }));
      setLiveDataLoading(prev => ({ ...prev, [blockType || 'all']: false }));
    }
  }, [loadConfig, loadCharacters, fetchLorebooks, refreshLoreEntries, selectedLorebook]);

  // Handle keyboard events for deleting nodes
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Delete' && selectedNode) {
        event.preventDefault();
        deleteSelectedNode();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [circuitStore.current, setNodes, setEdges, setSelectedNode]);

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const onDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const nodeType = event.dataTransfer.getData('nodeType');
    if (!nodeType) return;
    const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
    if (!reactFlowBounds) return;
    const blocksize = 100;
    const position = {
      x: event.clientX - reactFlowBounds.left - blocksize / 2,
      y: event.clientY - reactFlowBounds.top - blocksize / 2,
    };
    const config = blockConfigs[nodeType] || { inputs: [], outputs: [], label: 'Unknown Block' };
    const newNode: Node = {
      id: `${nodeType}-${Date.now()}`,
      type: nodeType,
      position,
      data: {
        label: config.label,
        type: nodeType,
        icon: getIconForType(nodeType),
        inputs: config.inputs,
        outputs: config.outputs
      },
    };
    setNodes((nds) => nds.concat(newNode));
  }, [setNodes]);

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => event.preventDefault(), []);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => setSelectedNode(node), []);

  // Function to update node data
  const updateNodeData = useCallback((nodeId: string, updates: any) => {
    console.log('updateNodeData called:', nodeId, updates);
    setNodes((prevNodes) => {
      return prevNodes.map((node) => {
        if (node.id === nodeId) {
          console.log('Updating node:', node.id, 'with:', updates);
          return {
            ...node,
            data: { ...node.data, ...updates }
          };
        }
        return node;
      });
    });
  }, [setNodes]);

  const getIconForType = (type: string) => {
    const icons: Record<string, string> = {
      // Basic blocks
      basic_text: '📝',
      boolean: '⚖️',
      switch: '🔀',

      // Data source blocks
      format_persona: '👤',
      character_current: '🎭',
      character_description: '📋',
      chat_history: '💬',

      // Variables and templates
      variables_substitution: '🔧',
      template_text_formatter: '📄',
      template_system_prompt: '⚙️',

      // Logic blocks
      logic_counter: '🔢',
      logic_random_number: '🎲',
      logic_random_choice: '🎯',
      logic_conditional: '🤔',
      logic_comparator: '⚖️',

      // Data manipulation
      data_string_concat: '🔗',
      data_string_split: '✂️',
      data_string_replace: '🔄',
      data_math_operation: '🧮',
      data_array_filter: '🔍',

      // Time and context
      time_current: '🕐',
      time_formatter: '📅',
      context_user_message: '💭',
      context_ai_response: '🤖',

      // Memory blocks
      memory_recent_messages: '🧠',
      memory_search: '🔎',

      // AI integration
      ai_command: '🧠',
      ai_model_selector: '🎭',
      ai_temperature: '🌡️',
      ai_max_context_tokens: '📏',

      // Endpoints
      endpoint_chat_reply: '💬',
      endpoint_image_generator: '🎨',

      // Legacy blocks
      logic: '',
      content: '📖',
      flow: '↗️',
      integration: '🔗',
    };
    return icons[type] || '⚡';
  };

  const onSave = () => {
    const currentCircuit = circuitStore.current;
    if (!currentCircuit) return;
    saveCircuit({ ...currentCircuit, data: { nodes, edges } }).catch(err => console.error('Failed to save:', err));
  };

  const handleCreateCircuit = async () => {
    if (!createForm.name.trim()) return;

    try {
      const newCircuit = {
        name: createForm.name.trim(),
        description: createForm.description.trim(),
        data: { nodes: [], edges: [] }
      };

      await saveCircuit(newCircuit);
      setCreateForm({ name: '', description: '' });
      setShowCreateForm(false);
    } catch (err) {
      console.error('Failed to create circuit:', err);
    }
  };

  const handleExecuteCircuit = async () => {
    if (!current) return;

    try {
      // Prepare context data for execution
      const contextData = {
        user_persona: userPersona,
        current_character_name: 'Test Character', // This would come from selected character
        current_character_id: 1, // This would come from selected character
        chat_history: [
          { role: 'user', content: 'Hello' },
          { role: 'assistant', content: 'Hi there!' }
        ],
        user_message: 'Test message',
        ai_response: 'Test response'
      };

      const result = await executeCircuit(current.id!, contextData);
      setExecutionLogs(result.logs);
      setExecutionOutputs(result.outputs);
      setShowExecutionResults(true);
    } catch (err) {
      console.error('Failed to execute circuit:', err);
    }
  };

  return (
    <div className="circuit-editor">
      <div className="toolbar panel">
        <span className="title">Circuits2</span>
        <div className="toolbar-actions">
          <button
            className="secondary"
            onClick={() => setShowCreateForm(true)}
            title="Create new circuit"
          >
            + New Circuit
          </button>
          <button
            className="secondary"
            onClick={onSave}
            disabled={!circuitStore.current}
            title="Save circuit"
          >
            Save Circuit
          </button>
          <button
            className="primary"
            onClick={handleExecuteCircuit}
            disabled={!circuitStore.current || isExecuting}
            title="Execute circuit"
          >
            {isExecuting ? '⏳ Executing...' : '🚀 Execute Circuit'}
          </button>
        </div>
      </div>

      {showCreateForm && (
        <div className="create-form-overlay">
          <div className="create-form-modal panel">
            <h3>Create New Circuit</h3>
            <div className="form-group">
              <label htmlFor="circuit-name">Name:</label>
              <input
                id="circuit-name"
                type="text"
                value={createForm.name}
                onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter circuit name..."
              />
            </div>
            <div className="form-group">
              <label htmlFor="circuit-description">Description (optional):</label>
              <textarea
                id="circuit-description"
                value={createForm.description}
                onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Enter circuit description..."
                rows={3}
              />
            </div>
            <div className="form-actions">
              <button onClick={handleCreateCircuit} disabled={!createForm.name.trim()}>
                Create Circuit
              </button>
              <button
                className="secondary"
                onClick={() => {
                  setShowCreateForm(false);
                  setCreateForm({ name: '', description: '' });
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="editor-body">
        <aside className="block-palette panel">
          <h4>Block Palette</h4>
          <div className="palette-items">
            {/* Basic Logic Blocks */}
            <div className="palette-section">
              <h5>Basic Blocks</h5>
            </div>
            {(['basic_text', 'boolean', 'switch'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Data Source Blocks */}
            <div className="palette-section">
              <h5>Data Sources</h5>
            </div>
            {(['format_persona', 'character_current', 'character_description', 'chat_history'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Variables and Templates */}
            <div className="palette-section">
              <h5>Variables & Templates</h5>
            </div>
            {(['variables_substitution', 'template_text_formatter', 'template_system_prompt'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Logic Blocks */}
            <div className="palette-section">
              <h5>Logic & Control</h5>
            </div>
            {(['logic_counter', 'logic_random_number', 'logic_random_choice', 'logic_conditional', 'logic_comparator'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Data Manipulation */}
            <div className="palette-section">
              <h5>Data Manipulation</h5>
            </div>
            {(['data_string_concat', 'data_string_split', 'data_string_replace', 'data_math_operation', 'data_array_filter'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Time and Context */}
            <div className="palette-section">
              <h5>Time & Context</h5>
            </div>
            {(['time_current', 'time_formatter', 'context_user_message', 'context_ai_response'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Memory Blocks */}
            <div className="palette-section">
              <h5>Memory</h5>
            </div>
            {(['memory_recent_messages', 'memory_search'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* AI Integration */}
            <div className="palette-section">
              <h5>AI Integration</h5>
            </div>
            {(['ai_command', 'ai_model_selector', 'ai_temperature', 'ai_max_context_tokens'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Endpoints */}
            <div className="palette-section">
              <h5>Endpoints</h5>
            </div>
            {(['endpoint_chat_reply', 'endpoint_image_generator'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}

            {/* Legacy System Blocks */}
            <div className="palette-section">
              <h5>Legacy System Blocks</h5>
            </div>
            {(['logic', 'content', 'flow', 'integration', 'system_main', 'system_tool_call', 'system_lore_suggest', 'system_image_summary', 'format_tools', 'format_lore_injection', 'char_system_prompt', 'char_personality', 'char_scenario', 'char_first_message', 'tool_image_request', 'tool_phone_url', 'tool_lore_suggestions', 'lorebook_content', 'lore_active_display', 'lore_title_injection'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{blockConfigs[type].label}</span>
              </div>
            ))}
          </div>
        </aside>

        <main className="canvas panel">
          <div className="canvas-header">
            {!current && circuits.length > 0 && <span className="muted">Select a circuit to view/edit</span>}
            {circuits.length === 0 && <span className="muted">No circuits available. Create your first circuit!</span>}
            {current && (
              <div className="execution-controls">
                <button
                  className="secondary"
                  onClick={() => setShowExecutionResults(!showExecutionResults)}
                  title="Toggle execution results"
                >
                  {showExecutionResults ? '📊 Hide Results' : '📊 Show Results'}
                </button>
              </div>
            )}
          </div>

          {circuits.length > 0 && !current && (
            <div className="circuits-list">
              {circuits.map((circuit: Circuit) => (
                <div
                  key={circuit.id || circuit.name}
                  className="circuit-item"
                  onClick={() => useCircuitStore.setState({ current: circuit })}
                >
                  <span className="circuit-name">{circuit.name}</span>
                  {circuit.description && (
                    <span className="circuit-description">{circuit.description}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {current && (
            <div className="circuit-canvas">
              <h3>{current.name}</h3>
              {/* Instructions for circuit editing:
               * How to use the circuit editor:
               * 1. Drag blocks from the Block Palette onto the canvas
               * 2. Notice the color-coded connectors:
               *    - GREEN connectors on the LEFT are INPUTS (data flows IN)
               *    - ORANGE connectors on the RIGHT are OUTPUTS (data flows OUT)
               * 3. Click and drag from an OUTPUT connector to an INPUT connector to connect blocks
               * 4. Blocks automatically expand taller to accommodate more connectors
               * 5. Click on a node to select it and view its properties in the properties panel
               * 6. Delete nodes by:
               *    - Pressing the Delete key when a node is selected
               *    - Clicking the "Delete Node" button in the properties panel
               * 7. Use the Controls panel for zoom/pan and MiniMap for overview navigation
               */}
              <div style={{ height: '100%', position: 'relative' }}>
                <div ref={reactFlowWrapper} style={{ height: `${containerHeight}px` }}>
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onNodeClick={onNodeClick}
                    nodeTypes={nodeTypes}
                    fitView
                  >
                    <Controls />
                    <MiniMap />
                  </ReactFlow>
                </div>
              </div>
            </div>
          )}

          {/* Execution Results Panel */}
          {showExecutionResults && current && (
            <div className="execution-results panel">
              <h4>🚀 Execution Results</h4>
              <div className="results-content">
                {/* Outputs Section */}
                {Object.keys(executionOutputs).length > 0 && (
                  <div className="results-section">
                    <h5>📤 Outputs</h5>
                    <div className="outputs-list">
                      {Object.entries(executionOutputs).map(([endpoint, output]) => (
                        <div key={endpoint} className="output-item">
                          <strong>{endpoint}:</strong>
                          <pre className="output-value">
                            {JSON.stringify(output, null, 2)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Logs Section */}
                <div className="results-section">
                  <h5>📝 Execution Logs</h5>
                  <div className="logs-container">
                    {executionLogs.length > 0 ? (
                      executionLogs.map((log, index) => (
                        <div key={index} className="log-entry">
                          <small>{log}</small>
                        </div>
                      ))
                    ) : (
                      <div className="no-logs">
                        <small>No execution logs available</small>
                      </div>
                    )}
                  </div>
                </div>

                {/* Execution Info */}
                {executionResult && (
                  <div className="results-section">
                    <h5>ℹ️ Execution Info</h5>
                    <div className="execution-info">
                      <div className="info-item">
                        <strong>ID:</strong> {executionResult.execution_id}
                      </div>
                      <div className="info-item">
                        <strong>Status:</strong>
                        <span className={executionResult.success ? 'status-success' : 'status-error'}>
                          {executionResult.success ? '✅ Success' : '❌ Failed'}
                        </span>
                      </div>
                      {executionResult.errors && executionResult.errors.length > 0 && (
                        <div className="info-item">
                          <strong>Errors:</strong>
                          <div className="error-list">
                            {executionResult.errors.map((error, index) => (
                              <div key={index} className="error-item">{error}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>

        <aside className="properties panel" key={propertiesKey}>
            <h4>Properties</h4>
           {current ? (
             <div className="properties-content">
               {selectedNode ? (
                 <>
                   {/* Block Settings Section */}
                   <div className="properties-section block-settings">
                     <h5>⚙️ Block Settings</h5>
                     {renderBlockSettings(selectedNode, updateNodeData)}
                   </div>

                   {/* Block Description */}
                   <div className="properties-section block-description">
                     <h5>📋 Block Description</h5>
                     <p className="block-description-text">{getBlockDescription(selectedNode.data.type)}</p>
                   </div>

                   {/* Current Values Section */}
                   <div className="properties-section current-values">
                     <h5>🔄 Current Values</h5>
                     {renderCurrentValues(selectedNode)}
                   </div>
                 </>
               ) : null}

               {!selectedNode ? (
                <>
                  <div className="property-item">
                    <strong>Name:</strong> {current.name}
                  </div>
                  {current.description && (
                    <div className="property-item">
                      <strong>Description:</strong> {current.description}
                    </div>
                  )}
                  <div className="property-item">
                    <strong>Nodes:</strong> {nodes.length}
                  </div>
                  <div className="property-item">
                    <strong>Edges:</strong> {edges.length}
                  </div>
                </>
              ) : (
                <>
                  <div className="property-item">
                    <strong>Label:</strong> {selectedNode.data.label}
                  </div>
                  <div className="property-item">
                    <strong>Type:</strong> {selectedNode.data.type}
                  </div>
                  <div className="property-item">
                    <strong>ID:</strong> {selectedNode.id}
                  </div>
                  <div className="property-item">
                    <strong>Position:</strong> ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
                  </div>

                  {/* Enhanced Properties for Content Blocks */}
                  {(() => {
                    const extendedConfig = blockExtendedConfigs[selectedNode.data.type];
                    if (!extendedConfig) return null;

                    return (
                      <>
                        {/* Connector Details Section */}
                        {(extendedConfig.connectorTypes?.inputs || extendedConfig.connectorTypes?.outputs) && (
                          <div className="properties-section">
                            <h5>🔗 Connector Details</h5>
                            {extendedConfig.connectorTypes.inputs && Object.keys(extendedConfig.connectorTypes.inputs).length > 0 && (
                              <div className="connector-group">
                                <div className="connector-header"><strong>Inputs:</strong></div>
                                {Object.entries(extendedConfig.connectorTypes.inputs).map(([name, type]) => (
                                  <div key={name} className="connector-item"
                                       title={`Input connector: ${name} (${type}) - Data flows into this connector`}>
                                    <span className="connector-name">{name}</span>
                                    <span className="connector-type">{type}</span>
                                    <span className="connector-status">●</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            {extendedConfig.connectorTypes.outputs && Object.keys(extendedConfig.connectorTypes.outputs).length > 0 && (
                              <div className="connector-group">
                                <div className="connector-header"><strong>Outputs:</strong></div>
                                {Object.entries(extendedConfig.connectorTypes.outputs).map(([name, type]) => (
                                  <div key={name} className="connector-item"
                                       title={`Output connector: ${name} (${type}) - Data flows out from this connector`}>
                                    <span className="connector-name">{name}</span>
                                    <span className="connector-type">{type}</span>
                                    <span className="connector-status">●</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Block Configuration Section */}
                        {extendedConfig.configuration && extendedConfig.configuration.length > 0 && (
                          <div className="properties-section">
                            <h5>⚙️ Configuration</h5>
                            {extendedConfig.configuration.map((config, index) => (
                              <div key={index} className="config-item"
                                   title={config.description || `${config.name} (${config.type})`}>
                                <strong>{config.name}:</strong>
                                <span className="config-value">[Not set]</span>
                                <span className="config-type">({config.type})</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Current Values Section */}
                        {selectedNode.data && Object.keys(selectedNode.data).length > 2 && (
                          <div className="properties-section">
                            <h5>📊 Current Values</h5>
                            {Object.entries(selectedNode.data).map(([key, value]) => {
                              if (['label', 'type', 'icon', 'inputs', 'outputs'].includes(key)) return null;
                              return (
                                <div key={key} className="value-item" title={`Current value for ${key}`}>
                                  <strong>{key}:</strong>
                                  <span>{typeof value === 'string' ? `"${value}"` : JSON.stringify(value)}</span>
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Metadata Section */}
                        {extendedConfig.metadata && extendedConfig.metadata.length > 0 && (
                          <div className="properties-section">
                            <h5>📋 Metadata</h5>
                            {extendedConfig.metadata.map((meta, index) => (
                              <div key={index} className="metadata-item" title={meta.description || meta.label}>
                                <strong>{meta.label}:</strong>
                                <span>{meta.value}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Live Data Section */}
                        {(selectedNode.data.type === 'format_persona' ||
                          selectedNode.data.type === 'format_tools' ||
                          selectedNode.data.type === 'format_lore_injection' ||
                          selectedNode.data.type.startsWith('char_') ||
                          selectedNode.data.type === 'variables_substitution' ||
                          selectedNode.data.type === 'lorebook_content' ||
                          selectedNode.data.type === 'lore_active_display' ||
                          selectedNode.data.type === 'lore_title_injection') && (
                          <div className="properties-section">
                            <h5>📊 Live Data</h5>
                            <div className="live-data-section">
                              {/* Format Persona Block */}
                              {selectedNode.data.type === 'format_persona' && (
                                <>
                                  <div className="live-data-item">
                                    <strong>User Name:</strong>
                                    <span className="data-display">
                                      {userPersona?.name || <span className="data-empty">Not set</span>}
                                    </span>
                                  </div>
                                  <div className="live-data-item">
                                    <strong>Description:</strong>
                                    <span className="data-display">
                                      {userPersona?.description || <span className="data-empty">Not set</span>}
                                    </span>
                                  </div>
                                </>
                              )}

                              {/* Format Tools Block */}
                              {selectedNode.data.type === 'format_tools' && (
                                <>
                                  <div className="live-data-item">
                                    <strong>Active Provider:</strong>
                                    <span className="data-display">{activeProvider || 'None'}</span>
                                  </div>
                                  <div className="live-data-item">
                                    <strong>Available Providers:</strong>
                                    <span className="data-display">{Object.keys(providers).length} configured</span>
                                  </div>
                                  <div className="live-data-details">
                                    {Object.entries(providers).map(([key, config]: [string, any]) => (
                                      <div key={key} className="provider-detail">
                                        <span className="provider-name">{key}</span>
                                        {config.model && <span className="provider-model">({config.model})</span>}
                                      </div>
                                    ))}
                                  </div>
                                </>
                              )}

                              {/* Format Lore Injection Block */}
                              {selectedNode.data.type === 'format_lore_injection' && (
                                <>
                                  <div className="live-data-item">
                                    <strong>Active Lorebook:</strong>
                                    <span className="data-display">
                                      {selectedLorebook?.name || <span className="data-empty">None selected</span>}
                                    </span>
                                  </div>
                                  <div className="live-data-item">
                                    <strong>Lore Entries:</strong>
                                    <span className="data-display">{loreEntries.length} entries</span>
                                  </div>
                                  <div className="live-data-details" style={{ maxHeight: '120px', overflowY: 'auto' }}>
                                    {loreEntries.slice(0, 5).map((entry: any) => (
                                      <div key={entry.id} className="lore-detail">
                                        <span className="lore-title">{entry.title}</span>
                                        <div className="lore-keywords">
                                          {entry.keywords?.length > 0 && (
                                            <small>Keys: {entry.keywords.slice(0, 3).join(', ')}</small>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                    {loreEntries.length > 5 && (
                                      <div className="lore-more">... and {loreEntries.length - 5} more entries</div>
                                    )}
                                  </div>
                                </>
                              )}

                              {/* Character Blocks */}
                              {selectedNode.data.type.startsWith('char_') && (
                                <>
                                  <div className="live-data-item">
                                    <strong>Loaded Characters:</strong>
                                    <span className="data-display">{characters.length} characters</span>
                                  </div>
                                  <div className="live-data-details live-data-details-scroll">
                                    {characters.slice(0, 5).map((char: any) => (
                                      <div key={char.id} className="character-detail">
                                        <span className="character-name">{char.name || 'Unnamed'}</span>
                                        {char.description && (
                                          <div className="character-desc">
                                            <small>{char.description.slice(0, 50)}...</small>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                    {characters.length > 5 && (
                                      <div className="character-more">... and {characters.length - 5} more characters</div>
                                    )}
                                  </div>
                                </>
                              )}

                              {/* Variables Substitution Block */}
                              {selectedNode.data.type === 'variables_substitution' && (
                                <>
                                  <div className="live-data-item">
                                    <strong>Variables Status:</strong>
                                    <span className="data-display">
                                      {promptsData ? 'Loaded' : <span className="data-empty">Not loaded</span>}
                                    </span>
                                  </div>
                                  {promptsData?.variables && (
                                    <div className="live-data-item">
                                      <strong>Variable Count:</strong>
                                      <span className="data-display">{Object.keys(promptsData.variables).length}</span>
                                    </div>
                                  )}
                                  {promptsData?.variables && (
                                    <div className="live-data-details live-data-details-scroll">
                                      {Object.entries(promptsData.variables).slice(0, 5).map(([key, value]: [string, any]) => (
                                        <div key={key} className="variable-detail">
                                          <span className="variable-key">{key}:</span>
                                          <span className="variable-value">{String(value).slice(0, 30)}...</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </>
                              )}

                              {/* Lorebook Content Block */}
                              {(selectedNode.data.type === 'lorebook_content' ||
                                selectedNode.data.type === 'lore_active_display' ||
                                selectedNode.data.type === 'lore_title_injection') && (
                                <>
                                  <div className="live-data-item">
                                    <strong>Lorebook:</strong>
                                    <span className="data-display">
                                      {selectedLorebook?.name || <span className="data-empty">None selected</span>}
                                    </span>
                                  </div>
                                  <div className="live-data-item">
                                    <strong>Total Entries:</strong>
                                    <span className="data-display">{loreEntries.length}</span>
                                  </div>
                                  {false && (
                                    <div className="loading-state">
                                      <small>Loading lore entries...</small>
                                    </div>
                                  )}
                                  {loreEntries.length > 0 && (
                                    <div className="live-data-details live-data-details-scroll">
                                      {loreEntries.slice(0, 3).map((entry: any) => (
                                        <div key={entry.id} className="entry-detail">
                                          <div className="entry-header">
                                            <span className="entry-title">{entry.title}</span>
                                            <small className="entry-trigger">T:{entry.trigger}</small>
                                          </div>
                                          <div className="entry-keywords">
                                            {entry.keywords?.length > 0 && (
                                              <small>K: {entry.keywords.slice(0, 2).join(', ')}</small>
                                            )}
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </>
                              )}

                              {/* Refresh button for all live data sections */}
                              <div className="live-data-actions live-data-actions-bordered">
                                <button
                                  className="secondary refresh-btn refresh-btn-small"
                                  onClick={() => refreshBlockData(selectedNode.data.type)}
                                  disabled={liveDataLoading[selectedNode.data.type]}
                                >
                                  {liveDataLoading[selectedNode.data.type] ? '⏳' : '🔄'} Refresh
                                </button>
                                {liveDataErrors[selectedNode.data.type] && (
                                  <div className="error-state">
                                    <small style={{ color: '#e74c3c' }}>
                                      ❌ {liveDataErrors[selectedNode.data.type]}
                                    </small>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    );
                  })()}

                  <div className="property-item">
                    <button
                      className="secondary delete-btn delete-btn-full"
                      onClick={deleteSelectedNode}
                      title="Delete selected node (or press Delete key)"
                    >
                      🗑️ Delete Node
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="muted">No circuit selected</div>
          )}
        </aside>
      </div>
    </div>
  );
};