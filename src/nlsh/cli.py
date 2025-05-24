"""Main CLI entrypoint for nlsh"""

import os
import sys
from typing import Optional, List
import typer
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import CompleteStyle

from .shell import ShellManager
from .llm import LLMInterface
from .langgraph_llm import LangGraphLLMInterface
from .context import ContextManager
from .history import HistoryManager

console = Console()
app = typer.Typer(help="Natural Language Shell - AI-augmented command line")

class CommandHistory:
    """Manages command history for arrow key navigation"""
    
    def __init__(self):
        self.history = InMemoryHistory()
        self.shell_history: List[str] = []
        self.llm_history: List[str] = []
    
    def add_command(self, command: str, command_type: str = "shell"):
        """Add a command to history"""
        self.history.append_string(command)
        
        if command_type == "shell":
            self.shell_history.append(command)
        else:
            self.llm_history.append(command)
    
    def get_recent_commands(self, limit: int = 10) -> List[str]:
        """Get recent commands from history"""
        all_commands = self.shell_history + self.llm_history
        return all_commands[-limit:]


@app.command()
def main(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
    use_langgraph: bool = typer.Option(True, "--use-langgraph/--use-simple", help="Use LangGraph interface")
):
    """Start the natural language shell"""
    
    # Initialize components
    shell_manager = ShellManager()
    context_manager = ContextManager()
    history_manager = HistoryManager()
    command_history = CommandHistory()
    
    # Initialize LLM interface
    try:
        if use_langgraph:
            llm_interface = LangGraphLLMInterface()
            console.print("[dim]Using LangGraph interface with tool calling[/dim]")
        else:
            llm_interface = LLMInterface()
            console.print("[dim]Using simple OpenAI interface[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to initialize LLM interface: {e}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)
    
    # Display welcome message
    console.print("[bold green]nlsh[/bold green] - Natural Language Shell")
    console.print(f"Detected shell: [cyan]{shell_manager.detected_shell}[/cyan]")
    console.print("Commands:")
    console.print("  [yellow]llm:[/yellow] <prompt> - Generate and execute shell commands")
    console.print("  [yellow]llm?[/yellow] <prompt> - Chat mode (information only)")
    console.print("  [yellow]exit[/yellow] or [yellow]quit[/yellow] - Exit nlsh")
    console.print("  [dim]Use ↑/↓ arrow keys for command history[/dim]\n")
    
    try:
        # Main shell loop
        while True:
            try:
                # Get current working directory for prompt
                cwd = os.getcwd()
                prompt_text = f"{os.path.basename(cwd)} $ "
                
                # Get user input with history support
                user_input = prompt(
                    prompt_text,
                    history=command_history.history,
                    complete_style=CompleteStyle.READLINE_LIKE
                ).strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                # Check for LLM commands
                if user_input.startswith('llm?'):
                    # Chat mode - information only
                    prompt_content = user_input[4:].strip()
                    if prompt_content:
                        command_history.add_command(user_input, "llm")
                        handle_llm_chat(
                            prompt_content,
                            shell_manager,
                            context_manager,
                            history_manager,
                            llm_interface,
                            use_langgraph
                        )
                    else:
                        console.print("[yellow]Please provide a prompt after 'llm?'[/yellow]")
                        
                elif user_input.startswith('llm:'):
                    # Command generation mode
                    prompt_content = user_input[4:].strip()
                    if prompt_content:
                        command_history.add_command(user_input, "llm")
                        handle_llm_command(
                            prompt_content,
                            shell_manager,
                            context_manager,
                            history_manager,
                            llm_interface,
                            use_langgraph
                        )
                    else:
                        console.print("[yellow]Please provide a prompt after 'llm:'[/yellow]")
                        
                else:
                    # Execute as regular shell command
                    command_history.add_command(user_input, "shell")
                    handle_shell_command(
                        user_input,
                        shell_manager,
                        context_manager,
                        history_manager
                    )
                    
            except KeyboardInterrupt:
                console.print("\nUse 'exit' to quit nlsh")
                continue
            except EOFError:
                break
                
    except KeyboardInterrupt:
        console.print("\nGoodbye!")
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    
    console.print("Goodbye!")


def handle_llm_chat(
    prompt: str,
    shell_manager: 'ShellManager',
    context_manager: 'ContextManager',
    history_manager: 'HistoryManager',
    llm_interface,
    use_langgraph: bool
):
    """Handle natural language chat (llm? mode)"""
    try:
        # Get current context
        context = context_manager.get_context()
        
        # Get shell info and add to context
        shell_info = shell_manager.get_shell_info()
        context.shell_info = shell_info
        
        # Generate chat response
        if use_langgraph and hasattr(llm_interface, 'generate_chat_response'):
            response = llm_interface.generate_chat_response(prompt, context)
        else:
            # Fallback to simple chat for original interface
            response = f"Chat mode not fully supported with simple interface. Try: {prompt}"
        
        # Display response as markdown for better formatting
        console.print("\n[yellow]AI Response:[/yellow]")
        if response.strip():
            markdown = Markdown(response)
            console.print(markdown)
        else:
            console.print("[dim]No response generated[/dim]")
        
        # Log the chat interaction
        history_manager.log_llm_interaction(
            user_prompt=prompt,
            generated_commands=[],  # No commands in chat mode
            executed_commands=[],
            execution_results=[],
            llm_model=getattr(llm_interface, 'model_name', 'unknown'),
            context_snapshot=context_manager.format_context_for_llm(context, shell_info)
        )
        
    except Exception as e:
        console.print(f"[red]Chat Error: {e}[/red]")


def handle_llm_command(
    prompt: str,
    shell_manager: 'ShellManager',
    context_manager: 'ContextManager',
    history_manager: 'HistoryManager',
    llm_interface,
    use_langgraph: bool
):
    """Handle natural language commands via LLM (llm: mode)"""
    try:
        # Get current context
        context = context_manager.get_context()
        
        # Get shell info and add to context
        shell_info = shell_manager.get_shell_info()
        context.shell_info = shell_info
        
        # Generate shell commands from LLM
        suggested_commands = llm_interface.generate_commands(prompt, context)
        
        if not suggested_commands:
            console.print("[yellow]No commands generated. Try rephrasing your request.[/yellow]")
            return
        
        # Display suggestions and get user confirmation
        console.print(f"\n[yellow]AI suggests:[/yellow]")
        for i, cmd in enumerate(suggested_commands, 1):
            console.print(f"  {i}. [cyan]{cmd}[/cyan]")
        
        if typer.confirm("\nExecute these commands?"):
            executed_commands = []
            execution_results = []
            
            for cmd in suggested_commands:
                console.print(f"\n[green]Executing:[/green] {cmd}")
                result = shell_manager.execute_command(cmd)
                
                executed_commands.append(cmd)
                execution_results.append(result)
                
                # Display output
                if result.output:
                    console.print(result.output)
                if result.error:
                    console.print(f"[red]Error:[/red] {result.error}")
                    
            # Log the interaction
            history_manager.log_llm_interaction(
                user_prompt=prompt,
                generated_commands=suggested_commands,
                executed_commands=executed_commands,
                execution_results=execution_results,
                llm_model=getattr(llm_interface, 'model_name', 'unknown'),
                context_snapshot=context_manager.format_context_for_llm(context, shell_info)
            )
        else:
            console.print("Commands cancelled")
            
    except Exception as e:
        console.print(f"[red]LLM Error: {e}[/red]")


def handle_shell_command(
    command: str,
    shell_manager: 'ShellManager',
    context_manager: 'ContextManager',
    history_manager: 'HistoryManager'
):
    """Handle regular shell commands"""
    try:
        result = shell_manager.execute_command(command)
        
        # Log the command
        history_manager.log_shell_command(command, result)
        
        # Display output
        if result.output:
            console.print(result.output)
        if result.error:
            console.print(f"[red]{result.error}[/red]")
            
    except Exception as e:
        console.print(f"[red]Shell Error: {e}[/red]")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent entries to show"),
    search: str = typer.Option(None, "--search", "-s", help="Search term"),
    entry_type: str = typer.Option(None, "--type", "-t", help="Entry type (shell_command, llm_interaction)")
):
    """Show command history"""
    history_manager = HistoryManager()
    
    if search:
        entries = history_manager.search_history(search, entry_type)
    else:
        entries = history_manager.get_recent_commands(limit, entry_type)
    
    if not entries:
        console.print("No history entries found")
        return
    
    console.print(f"\n[bold]Command History[/bold] ({len(entries)} entries)")
    console.print("=" * 50)
    
    for entry in reversed(entries):  # Show most recent first
        timestamp = entry['timestamp']
        entry_data = entry['data']
        
        console.print(f"\n[dim]{timestamp}[/dim] - [cyan]{entry['entry_type']}[/cyan]")
        
        if entry['entry_type'] == 'shell_command':
            console.print(f"Command: [green]{entry_data.get('command', 'unknown')}[/green]")
            if entry_data.get('return_code', 0) != 0:
                console.print(f"[red]Exit code: {entry_data.get('return_code')}[/red]")
        
        elif entry['entry_type'] == 'llm_interaction':
            console.print(f"Prompt: [yellow]{entry_data.get('user_prompt', 'unknown')}[/yellow]")
            generated = entry_data.get('generated_commands', [])
            if generated:
                console.print(f"Generated: [cyan]{', '.join(generated)}[/cyan]")


@app.command()
def stats():
    """Show usage statistics"""
    history_manager = HistoryManager()
    stats = history_manager.get_command_stats()
    
    console.print("\n[bold]nlsh Usage Statistics[/bold]")
    console.print("=" * 30)
    
    console.print(f"Total entries: {stats.get('total_entries', 0)}")
    
    by_type = stats.get('by_type', {})
    if by_type:
        console.print("\nBy type:")
        for entry_type, count in by_type.items():
            console.print(f"  {entry_type}: {count}")
    
    recent_activity = stats.get('recent_activity', {})
    if recent_activity:
        console.print("\nRecent activity (last 7 days):")
        for date, count in list(recent_activity.items())[:7]:
            console.print(f"  {date}: {count} commands")


if __name__ == "__main__":
    app() 