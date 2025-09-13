# Circuit Block Types and definitions

## Text Block
 - **Description**: Simple Text block that can send strings or integers
 - **Inputs**: 0
 - **Outputs**: 1 output named Output Text
 - **Settings**:  
     - 1 multi-line text input form named Text Content.
     - 1 drop-down named Output Type with the options String and Numerical
 - **Additional Notes**: Outputs the text added into Text Content if Output type = string.  If Output Type = numerical only numbers will be accepted in the Text Content field and the output will be sent as an int instead of string

 ## Current Character
 - **Description**: Outputs the currently active character's name and numerical character ID.
 - **Inputs**: 0
 - **Outputs**: 2  
    - Character Name - outputs the currently selected active Character's name
    - character_id - outputs the numerical character_id (just a number that uniquely identifies which character is selected) for the currently selected active Character.
 - **Settings**: No settings necessary
 - **Additional Notes**:

 ## Chat History
 - **Description**: A block which sends the chat history of the active chat. 
 - **Inputs**: 0
 - **Outputs**: 1 - Chat History Output
 - **Settings**: 2  
     - Message Type - dropdown - allows selecting either All Messages (default), User Messages, AI Replies or other (System Messages).
     - Message Count - numerical input field
 - **Additional Notes**: Will output *entire* message history if Message Count is blank or equal to 0. If there is a number in message history will only output the most recent *x* messages where *x* is the number entered into Message Count. If Message Type is set to a value other than all messages will only output messages of the selected type.

 ## Variable
 - **Description**: allows outputting of user-defined variables (from Settings->Prompts->Variables) or pre-defined "placeholders" (like the ones listed in System Prompts in Settings->Prompts->System Prompts)
 - **Inputs**: 0
 - **Outputs**: 1 - Variable Output
 - **Settings**: 2  
    - Variable - drop-down - dynamically populates with all the variables created under System->Prompt->Variables as well as all the placeholders built-into the app. 
 - **Additional Notes**: Variable output simply outputs the value of the selected variable.

 ## Combiner
 - **Description**: This is how we can combine all the different blocks output into a single output block.
 - **Inputs**: 2+
    - Starts with 2 basic inputs but can dynamically increase the number of inputs using the slider in Settings
 - **Outputs**: 1 - Combied Output
 - **Settings**: 3  
    - Inputs - slider with integers from 2 to 8. The number of inputs available on the block will dynamically change and update based on the value of this slider. For example, if th slider is set to 4 we should have 4 inputs on the block (***Note: If React Flow is unable to dynamically update the number of inputs on a node and/or this is very difficult to implement please notify me and we can discuss an alternative method***)
     - Separator - text input field - This is just a basic input field that will define the separator that will be used between the inputs. Most of the time it'll probably just be a comma. But if we had 3 inputs with their values set to input1, input2, and input3 respectively and the Separator field was set to "-" the output of this block would then be input1-input2-input3
 - **Additional Notes**:  



## Circuit Implementation Notes from AI

- **Variables/Placeholders Block Settings Issue**: The settings panel for Variables/Placeholders blocks may not appear correctly, potentially due to rendering issues in the UI. This affects the ability to configure variable selections dynamically. Workaround: Refresh the circuit editor or reload the page to force re-rendering of the settings panel.

- **Constructor Block Missing Inputs Setting**: The constructor block lacks a dedicated "inputs" setting to specify the number of inputs programmatically. Currently, input count is handled through manual configuration or defaults. Known limitation: Dynamic input adjustment requires manual intervention or code-level changes.

- **Properties Panel Display Problems**: The Properties Panel does not consistently show inputs and outputs for certain blocks, especially when switching between block types or during circuit updates. This can lead to confusion about block connectivity. Workaround: Toggle the properties panel visibility or select/deselect the block to trigger updates.

- **Current Workarounds and Known Limitations**:
  - Manual refresh often resolves UI rendering issues.
  - Input/output counts are currently static for most blocks except Combiner.
  - Block connections may need verification after circuit modifications.
  - Performance may degrade with large numbers of blocks due to React Flow limitations.

- **Technical Details on Data Store Integration**: The circuit system integrates with the data store via circuitStore.ts, which manages state persistence and block configurations. Dynamic dropdowns for variables are populated through API calls to fetch available variables and placeholders. Data synchronization occurs on circuit save/load, ensuring consistency between UI and backend state.