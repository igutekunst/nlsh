"""Streaming interface with animated progress spinners"""

import time
import threading
from typing import Iterator, Any, Dict, Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

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
    """Handle streaming responses with tool call animations"""
    
    def __init__(self):
        self.current_spinner: Optional[AnimatedSpinner] = None
        self.tool_results = []
    
    def start_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """Start animation for a tool call"""
        if self.current_spinner:
            self.current_spinner.stop()
        
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
            
            # Show result if it's informational
            if result and len(result.strip()) > 0:
                # Truncate long results for display
                display_result = result[:200] + "..." if len(result) > 200 else result
                console.print(Panel(display_result, title="Tool Result", border_style="blue"))
    
    def stream_text(self, text_chunk: str):
        """Stream text content as it arrives"""
        # If we have a spinner running, we're still in tool mode
        if not self.current_spinner:
            # Print text directly for streaming
            print(text_chunk, end="", flush=True)
    
    def finish_streaming(self):
        """Finish the streaming session"""
        if self.current_spinner:
            self.current_spinner.stop()
            self.current_spinner = None
        
        print()  # Add final newline
    
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
    
    def __init__(self):
        self.pending_confirmations = []
    
    def request_confirmation(self, command: str) -> bool:
        """Request confirmation for a command with nice formatting"""
        console.print()  # Add space
        console.print(Panel(
            f"[yellow]Command to execute:[/yellow]\n[cyan]{command}[/cyan]",
            title="⚠️  Confirmation Required",
            border_style="yellow"
        ))
        
        # Use typer for confirmation
        import typer
        return typer.confirm("Execute this command?")


def create_streaming_interface() -> tuple[StreamingResponse, ConfirmationHandler]:
    """Create a streaming interface with confirmation handler"""
    return StreamingResponse(), ConfirmationHandler() 