"""LangGraph-based LLM interface with tool calling"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated

from .context import ContextInfo
from .tools import AVAILABLE_TOOLS, set_shell_manager, set_confirmation_callback
from .streaming import create_streaming_interface, StreamingResponse, ConfirmationHandler


class GraphState(TypedDict):
    """State for the LangGraph workflow"""
    messages: Annotated[list, add_messages]
    context: Optional[ContextInfo]
    mode: str  # 'chat' or 'command'
    commands: List[str]


class LangGraphLLMInterface:
    """LangGraph-based LLM interface with tool calling"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Initialize LangChain OpenAI model with tools
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.1,
            api_key=api_key,
            streaming=True  # Enable streaming
        )
        
        # Bind tools to the model
        self.llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
        
        # Create tool node
        self.tool_node = ToolNode(AVAILABLE_TOOLS)
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Initialize streaming components
        self.streaming_response = None
        self.confirmation_handler = None
        
        # History manager for logging tool calls
        self.history_manager = None
    
    def setup_shell_integration(self, shell_manager, confirmation_callback=None):
        """Setup shell manager and confirmation callback for tools"""
        set_shell_manager(shell_manager)
        
        if confirmation_callback:
            set_confirmation_callback(confirmation_callback)
        else:
            # Create default confirmation handler
            streaming_response, confirmation_handler = create_streaming_interface()
            self.streaming_response = streaming_response
            self.confirmation_handler = confirmation_handler
            set_confirmation_callback(confirmation_handler.request_confirmation)
    
    def setup_history_integration(self, history_manager):
        """Setup history manager for logging interactions and tool calls"""
        self.history_manager = history_manager
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        def should_continue(state: GraphState) -> str:
            """Decide whether to continue with tools or end"""
            last_message = state["messages"][-1]
            
            # If there are tool calls, continue to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            
            # Otherwise, end
            return END
        
        def call_model(state: GraphState) -> Dict[str, Any]:
            """Call the LLM model"""
            messages = state["messages"]
            mode = state.get("mode", "chat")
            
            # Create system message based on mode
            if mode == "command":
                system_msg = self._create_command_system_message(state.get("context"))
            else:  # chat mode
                system_msg = self._create_chat_system_message(state.get("context"))
            
            # Add system message if not already present
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [system_msg] + messages
            
            response = self.llm_with_tools.invoke(messages)
            
            # Update state
            return {"messages": [response]}
        
        # Create workflow
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", self.tool_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END,
            }
        )
        
        # Tools always go back to agent
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def generate_chat_response(self, prompt: str, context: ContextInfo) -> str:
        """Generate a chat response using LangGraph (llm? mode)"""
        try:
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "context": context,
                "mode": "chat",
                "commands": []
            }
            
            # Run the graph
            result = self.graph.invoke(initial_state)
            
            # Extract the final response
            last_message = result["messages"][-1]
            if isinstance(last_message, AIMessage):
                return last_message.content
            
            return "No response generated"
            
        except Exception as e:
            raise Exception(f"LLM API error: {e}")
    
    def generate_commands(self, prompt: str, context: ContextInfo) -> List[str]:
        """Generate shell commands using LangGraph (llm: mode)"""
        try:
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "context": context,
                "mode": "command",
                "commands": []
            }
            
            # Run the graph
            result = self.graph.invoke(initial_state)
            
            # Extract commands from the final response
            last_message = result["messages"][-1]
            if isinstance(last_message, AIMessage):
                commands = self._parse_commands(last_message.content)
                return commands
            
            return []
            
        except Exception as e:
            raise Exception(f"LLM API error: {e}")
    
    def _create_chat_system_message(self, context: ContextInfo = None) -> SystemMessage:
        """Create system message for chat mode"""
        
        system_content = """You are a helpful AI assistant with access to shell and file system tools.

Use shell commands and tools whenever appropriate to provide accurate, up-to-date information about the user's environment.

You can help users with:
- File and directory operations
- Git repository information
- System information
- General questions and assistance

You have access to tools that can:
- List files and directories
- Read file contents
- Find files matching patterns
- Get git status and logs
- Get system information
- Get directory trees
- Execute shell commands (with confirmation)

IMPORTANT: Always use tools proactively when they would help answer the question or provide better information. For example:
- If asked about files, use list_files or read_file tools
- If asked about the current directory, use get_working_directory
- If asked about git, use git_status or git_log tools
- If asked about system info, use get_system_info
- If the user wants to perform an action, suggest using the execute_shell_command tool

Don't rely solely on the provided context - use tools to get fresh, accurate information whenever relevant.
"""
        
        if context:
            from .context import ContextManager
            context_manager = ContextManager()
            formatted_context = context_manager.format_context_for_llm(context, context.shell_info)
            system_content += f"\n\nCurrent Context:\n{formatted_context}"
        
        return SystemMessage(content=system_content)
    
    def _create_command_system_message(self, context: ContextInfo = None) -> SystemMessage:
        """Create system message for command generation mode"""
        
        shell_name = context.shell_info.get('name', 'bash') if context else 'bash'
        
        system_content = f"""You are an expert command-line assistant that generates {shell_name} shell commands.

Use shell commands and tools whenever appropriate to understand the environment before generating commands.

Key Guidelines:
1. ALWAYS use tools to understand the current environment first before generating commands
2. Use list_files, read_file, get_working_directory, git_status, and other tools proactively
3. Generate ONLY valid {shell_name} commands that can be executed directly
4. Respond with one or more commands, each on a separate line
5. Do NOT include explanations, comments, or markdown formatting
6. Do NOT use backticks or code blocks
7. Be precise and safe - avoid destructive operations unless explicitly requested
8. Consider the current working directory and available files
9. Use the execute_shell_command tool if the user wants immediate execution

IMPORTANT: Don't guess about the environment - use tools to gather current information first, then provide appropriate commands based on what you discover.

After using tools to gather information, provide your final response as shell commands only.

Example Response Format:
ls -la
cd subdirectory
grep -r "pattern" *.txt

Remember: Your final response should contain ONLY the commands, nothing else.
"""
        
        if context:
            from .context import ContextManager
            context_manager = ContextManager()
            formatted_context = context_manager.format_context_for_llm(context, context.shell_info)
            system_content += f"\n\nCurrent Context:\n{formatted_context}"
        
        return SystemMessage(content=system_content)
    
    def _parse_commands(self, response_text: str) -> List[str]:
        """Parse commands from LLM response"""
        if not response_text:
            return []
        
        # Clean up the response
        response_text = response_text.strip()
        
        # Split into lines and clean each command
        lines = response_text.split('\n')
        commands = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Skip obvious non-command lines (explanations, etc.)
            if line.startswith('#') or line.startswith('//'):
                continue
            if line.startswith('Here') or line.startswith('The command'):
                continue
            if '```' in line:
                continue
            if line.startswith('I ') or line.startswith('Based on'):
                continue
                
            # Remove any numbering (1. command, - command, etc.)
            import re
            if re.match(r'^\d+\.?\s+', line):
                line = re.sub(r'^\d+\.?\s+', '', line)
            elif line.startswith('- '):
                line = line[2:].strip()
            elif line.startswith('* '):
                line = line[2:].strip()
                
            # Basic validation - should look like a command
            if line and not line.isspace() and not line.startswith('After'):
                commands.append(line)
        
        return commands[:5]  # Limit to 5 commands max for safety
    
    def validate_api_key(self) -> bool:
        """Validate that OpenAI API key is working"""
        try:
            # Make a minimal API call to test the key
            response = self.llm.invoke([HumanMessage(content="test")])
            return True
        except Exception:
            return False
    
    def generate_chat_response_streaming(self, prompt: str, context: ContextInfo) -> str:
        """Generate a chat response using LangGraph with streaming (llm? mode)"""
        try:
            # Setup streaming
            if not self.streaming_response:
                self.streaming_response, self.confirmation_handler = create_streaming_interface()
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "context": context,
                "mode": "chat",
                "commands": []
            }
            
            # Stream the graph execution
            response_content = ""
            current_tool_calls = {}  # Track tool calls for logging
            agent_execution_count = 0  # Track agent executions
            
            print()  # Add some space before streaming starts
            
            for event in self.graph.stream(initial_state):
                for node_name, node_output in event.items():
                    if node_name == "agent":
                        agent_execution_count += 1
                        # Handle AI response
                        messages = node_output.get("messages", [])
                        for message in messages:
                            if isinstance(message, AIMessage):
                                if hasattr(message, 'tool_calls') and message.tool_calls:
                                    # Handle tool calls with animation
                                    for tool_call in message.tool_calls:
                                        tool_name = tool_call.get('name', 'unknown_tool')
                                        tool_args = tool_call.get('args', {})
                                        tool_id = tool_call.get('id', str(len(current_tool_calls)))
                                        
                                        # Store for later logging
                                        current_tool_calls[tool_id] = {
                                            'name': tool_name,
                                            'args': tool_args
                                        }
                                        
                                        self.streaming_response.start_tool_call(tool_name, tool_args)
                                else:
                                    # Stream text content token by token if available
                                    content = getattr(message, 'content', '')
                                    if content:
                                        # For the final agent response (after tools), stream the new content
                                        if agent_execution_count > 1 or not current_tool_calls:
                                            # This is either the final response after tools or a response without tools
                                            new_content = content[len(response_content):]
                                            if new_content:
                                                # Stream character by character for better effect
                                                for char in new_content:
                                                    self.streaming_response.stream_text_token(char)
                                                    import time
                                                    time.sleep(0.01)  # Small delay for streaming effect
                                        # Always update response_content with the latest content
                                        response_content = content
                                        
                    elif node_name == "tools":
                        # Handle tool results
                        messages = node_output.get("messages", [])
                        for message in messages:
                            if hasattr(message, 'content') and hasattr(message, 'tool_call_id'):
                                tool_result = message.content
                                tool_id = message.tool_call_id
                                
                                # Log tool call to history if we have a history manager
                                if self.history_manager and tool_id in current_tool_calls:
                                    tool_info = current_tool_calls[tool_id]
                                    self.history_manager.log_tool_call(
                                        tool_name=tool_info['name'],
                                        tool_args=tool_info['args'],
                                        tool_result=tool_result
                                    )
                                
                                self.streaming_response.finish_tool_call(tool_result)
            
            self.streaming_response.finish_streaming()
            return response_content or "No response generated"
            
        except Exception as e:
            if self.streaming_response:
                self.streaming_response.finish_streaming()
            raise Exception(f"LLM API error: {e}")
    
    def generate_commands_streaming(self, prompt: str, context: ContextInfo) -> List[str]:
        """Generate shell commands using LangGraph with streaming (llm: mode)"""
        try:
            # Setup streaming
            if not self.streaming_response:
                self.streaming_response, self.confirmation_handler = create_streaming_interface()
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "context": context,
                "mode": "command",
                "commands": []
            }
            
            # Stream the graph execution
            final_response = ""
            current_tool_calls = {}  # Track tool calls for logging
            agent_execution_count = 0  # Track agent executions
            
            print()  # Add some space before streaming starts
            
            for event in self.graph.stream(initial_state):
                for node_name, node_output in event.items():
                    if node_name == "agent":
                        agent_execution_count += 1
                        # Handle AI response
                        messages = node_output.get("messages", [])
                        for message in messages:
                            if isinstance(message, AIMessage):
                                if hasattr(message, 'tool_calls') and message.tool_calls:
                                    # Handle tool calls with animation
                                    for tool_call in message.tool_calls:
                                        tool_name = tool_call.get('name', 'unknown_tool')
                                        tool_args = tool_call.get('args', {})
                                        tool_id = tool_call.get('id', str(len(current_tool_calls)))
                                        
                                        # Store for later logging
                                        current_tool_calls[tool_id] = {
                                            'name': tool_name,
                                            'args': tool_args
                                        }
                                        
                                        self.streaming_response.start_tool_call(tool_name, tool_args)
                                else:
                                    # Stream text content
                                    content = getattr(message, 'content', '')
                                    if content:
                                        # For the final agent response (after tools), stream the new content
                                        if agent_execution_count > 1 or not current_tool_calls:
                                            # This is either the final response after tools or a response without tools
                                            new_content = content[len(final_response):]
                                            if new_content:
                                                # Stream character by character for better effect
                                                for char in new_content:
                                                    self.streaming_response.stream_text_token(char)
                                                    import time
                                                    time.sleep(0.01)  # Small delay for streaming effect
                                        # Always update final_response with the latest content
                                        final_response = content
                                        
                    elif node_name == "tools":
                        # Handle tool results
                        messages = node_output.get("messages", [])
                        for message in messages:
                            if hasattr(message, 'content') and hasattr(message, 'tool_call_id'):
                                tool_result = message.content
                                tool_id = message.tool_call_id
                                
                                # Log tool call to history if we have a history manager
                                if self.history_manager and tool_id in current_tool_calls:
                                    tool_info = current_tool_calls[tool_id]
                                    self.history_manager.log_tool_call(
                                        tool_name=tool_info['name'],
                                        tool_args=tool_info['args'],
                                        tool_result=tool_result
                                    )
                                
                                self.streaming_response.finish_tool_call(tool_result)
            
            self.streaming_response.finish_streaming()
            
            # Extract commands from the final response
            if final_response:
                commands = self._parse_commands(final_response)
                return commands
            
            return []
            
        except Exception as e:
            if self.streaming_response:
                self.streaming_response.finish_streaming()
            raise Exception(f"LLM API error: {e}") 