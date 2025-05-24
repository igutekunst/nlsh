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
from .tools import AVAILABLE_TOOLS


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
            api_key=api_key
        )
        
        # Bind tools to the model
        self.llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
        
        # Create tool node
        self.tool_node = ToolNode(AVAILABLE_TOOLS)
        
        # Build the graph
        self.graph = self._build_graph()
    
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

Use these tools when helpful to answer the user's questions. Provide informative and helpful responses.

For questions about the current environment, use the available tools to get up-to-date information.
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

You can use available tools to gather information before generating commands.

Key Guidelines:
1. Use tools to understand the current environment first
2. Generate ONLY valid {shell_name} commands that can be executed directly
3. Respond with one or more commands, each on a separate line
4. Do NOT include explanations, comments, or markdown formatting
5. Do NOT use backticks or code blocks
6. Be precise and safe - avoid destructive operations unless explicitly requested
7. Consider the current working directory and available files

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