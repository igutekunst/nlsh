"""Streaming interface with animated progress spinners"""

import time
import threading
import asyncio
import sys
from typing import Iterator, Any, Dict, Optional, Callable, AsyncIterator, Union
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

from .utils import confirm_action

console = Console()


class AnimatedSpinner:
    """Animated spinner for tool calls"""
    
    def __init__(self, message: str, spinner_name: str = "dots"):
        self.message = message
        self.spinner = Spinner(spinner_name, text=message)
        self.is_running = False
        self._thread = None
        self._live = None
    
    def start(self):
        """Start the spinner animation"""
        if self.is_running:
            return
            
        self.is_running = True
        self._live = Live(self.spinner, console=console, refresh_per_second=10)
        self._live.start()
    
    def update(self, message: str):
        """Update the spinner message"""
        self.message = message
        if self._live:
            self.spinner.text = message
            self._live.update(self.spinner)
    
    def stop(self, final_message: str = None):
        """Stop the spinner animation"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self._live:
            self._live.stop()
            self._live = None
        
        # Show final message
        if final_message:
            console.print(f"✓ {final_message}", style="green")
        else:
            console.print(f"✓ {self.message}", style="green")


class StreamingResponse:
    """Handle streaming responses with tool call animations and real-time text"""
    
    def __init__(self):
        self.current_spinner: Optional[AnimatedSpinner] = None
        self.tool_results = []
        self._in_tool_mode = False
    
    def start_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """Start animation for a tool call"""
        if self.current_spinner:
            self.current_spinner.stop()
        
        self._in_tool_mode = True
        
        # Create a nice message for the tool call
        message = self._format_tool_message(tool_name, args)
        self.current_spinner = AnimatedSpinner(message, "dots12")
        self.current_spinner.start()
    
    def finish_tool_call(self, result: str):
        """Finish the current tool call animation"""
        if self.current_spinner:
            # Show the result briefly
            final_message = f"Tool completed"
            self.current_spinner.stop(final_message)
            self.current_spinner = None
            
            # Show result if it's informational (but don't overwhelm with huge output)
            if result and len(result.strip()) > 0:
                # Truncate long results for display
                display_result = result[:200] + "..." if len(result) > 200 else result
                console.print(Panel(display_result, title="Tool Result", border_style="blue"))
        
        self._in_tool_mode = False
    
    def stream_text_token(self, token: str):
        """Stream individual tokens as they arrive from LLM"""
        # Only stream text if we're not in tool mode
        if not self._in_tool_mode:
            print(token, end="", flush=True)
    
    def stream_text_chunk(self, text_chunk: str):
        """Stream text content as it arrives (for chunks rather than tokens)"""
        # Only stream text if we're not in tool mode
        if not self._in_tool_mode:
            print(text_chunk, end="", flush=True)

    async def stream_command_output(self, command_stream: AsyncIterator[tuple[str, str]]):
        """Stream command output in real-time"""
        async for stream_type, content in command_stream:
            if stream_type == 'stdout':
                print(content, end="", flush=True)
            elif stream_type == 'stderr':
                print(content, end="", file=sys.stderr, flush=True)
            elif stream_type == 'exit':
                if content != '0':
                    console.print(f"\n[red]Command exited with code: {content}[/red]")
                return int(content)
        return 0
    
    def finish_streaming(self):
        """Finish the streaming session"""
        if self.current_spinner:
            self.current_spinner.stop()
            self.current_spinner = None
        
        if not self._in_tool_mode:
            print()  # Add final newline for text streaming
    
    def _format_tool_message(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format a nice message for tool calls"""
        tool_messages = {
            "list_files": lambda a: f"📁 Listing files in {a.get('path', 'directory')}",
            "read_file": lambda a: f"📄 Reading file: {a.get('path', 'file')}",
            "find_files": lambda a: f"🔍 Finding files matching '{a.get('pattern', 'pattern')}'",
            "execute_shell_command": lambda a: f"⚡ Preparing to run: {a.get('command', 'command')}",
            "git_status": lambda a: "📊 Checking git status",
            "git_log": lambda a: "📜 Getting git log",
            "get_system_info": lambda a: "💻 Getting system information",
            "get_working_directory": lambda a: "📍 Getting current directory",
            "get_directory_tree": lambda a: f"🌳 Getting directory tree for {a.get('path', 'path')}",
            "get_file_info": lambda a: f"ℹ️  Getting info for {a.get('path', 'path')}"
        }
        
        formatter = tool_messages.get(tool_name)
        if formatter:
            try:
                return formatter(args)
            except:
                pass
        
        return f"🔧 Running {tool_name.replace('_', ' ')}"


class ConfirmationHandler:
    """Handle interactive confirmations during streaming"""
    
    def __init__(self, streaming_response: Optional[Union['StreamingResponse', 'AsyncStreamingResponse']] = None):
        self.pending_confirmations = []
        self.streaming_response = streaming_response
    
    def request_confirmation(self, command: str) -> bool:
        """Request confirmation for a command with simple y/n prompt"""
        # Stop any active spinner to prevent display conflicts
        spinner_was_running = False
        if self.streaming_response and self.streaming_response.current_spinner:
            spinner_was_running = True
            self.streaming_response.current_spinner.stop()
        
        console.print()  # Add space
        console.print(Panel(
            f"[yellow]Command to execute:[/yellow]\n[cyan]{command}[/cyan]",
            title="⚠️  Confirmation Required",
            border_style="yellow"
        ))
        
        result = confirm_action("Do you want to execute this command?")
        
        # Restart spinner if it was running (for cases where we want to continue the tool)
        # Note: This is mainly for consistency, though typically after confirmation 
        # the tool execution will start a new spinner anyway
        
        return result


class AsyncStreamingResponse:
    """Async version of streaming response for better integration with async operations"""
    
    def __init__(self):
        self.current_spinner: Optional[AnimatedSpinner] = None
        self._in_tool_mode = False
        self._console = Console()
    
    async def start_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """Start animation for a tool call"""
        if self.current_spinner:
            self.current_spinner.stop()
        
        self._in_tool_mode = True
        
        # Create a nice message for the tool call
        message = self._format_tool_message(tool_name, args)
        self.current_spinner = AnimatedSpinner(message, "dots12")
        self.current_spinner.start()
    
    async def finish_tool_call(self, result: str):
        """Finish the current tool call animation"""
        if self.current_spinner:
            final_message = f"Tool completed"
            self.current_spinner.stop(final_message)
            self.current_spinner = None
            
            if result and len(result.strip()) > 0:
                display_result = result[:200] + "..." if len(result) > 200 else result
                self._console.print(Panel(display_result, title="Tool Result", border_style="blue"))
        
        self._in_tool_mode = False
    
    async def stream_llm_tokens(self, token_stream: AsyncIterator[str]):
        """Stream LLM tokens in real-time"""
        async for token in token_stream:
            if not self._in_tool_mode:
                print(token, end="", flush=True)
    
    async def stream_command_output(self, command_stream: AsyncIterator[tuple[str, str]]):
        """Stream command output in real-time"""
        exit_code = 0
        async for stream_type, content in command_stream:
            if stream_type == 'stdout':
                print(content, end="", flush=True)
            elif stream_type == 'stderr':
                print(content, end="", file=sys.stderr, flush=True)
            elif stream_type == 'exit':
                exit_code = int(content)
                if exit_code != 0:
                    self._console.print(f"\n[red]Command exited with code: {exit_code}[/red]")
        return exit_code
    
    def _format_tool_message(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format a nice message for tool calls"""
        tool_messages = {
            "list_files": lambda a: f"📁 Listing files in {a.get('path', 'directory')}",
            "read_file": lambda a: f"📄 Reading file: {a.get('path', 'file')}",
            "find_files": lambda a: f"🔍 Finding files matching '{a.get('pattern', 'pattern')}'",
            "execute_shell_command": lambda a: f"⚡ Preparing to run: {a.get('command', 'command')}",
            "git_status": lambda a: "📊 Checking git status",
            "git_log": lambda a: "📜 Getting git log",
            "get_system_info": lambda a: "💻 Getting system information",
            "get_working_directory": lambda a: "📍 Getting current directory",
            "get_directory_tree": lambda a: f"🌳 Getting directory tree for {a.get('path', 'path')}",
            "get_file_info": lambda a: f"ℹ️  Getting info for {a.get('path', 'path')}"
        }
        
        formatter = tool_messages.get(tool_name)
        if formatter:
            try:
                return formatter(args)
            except:
                pass
        
        return f"🔧 Running {tool_name.replace('_', ' ')}"


def create_streaming_interface() -> tuple[StreamingResponse, ConfirmationHandler]:
    """Create a streaming interface with confirmation handler"""
    streaming_response = StreamingResponse()
    confirmation_handler = ConfirmationHandler(streaming_response)
    return streaming_response, confirmation_handler


def create_async_streaming_interface() -> tuple[AsyncStreamingResponse, ConfirmationHandler]:
    """Create an async streaming interface with confirmation handler"""
    streaming_response = AsyncStreamingResponse()
    confirmation_handler = ConfirmationHandler(streaming_response)
    return streaming_response, confirmation_handler 