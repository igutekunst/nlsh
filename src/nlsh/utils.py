"""Utility functions for nlsh"""

import sys
import termios
import tty
from rich.console import Console

console = Console()


def get_single_char():
    """Get a single character from stdin without pressing Enter (Unix only)"""
    try:
        # Save current terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            # Read single character
            ch = sys.stdin.read(1)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        return ch
    except (ImportError, OSError):
        # Fallback to regular input if termios isn't available (Windows)
        return input().lower()


def confirm_action(message: str = "Continue?", show_options: bool = True) -> bool:
    """
    Get confirmation with single-key input (y/n/q without Enter)
    
    Args:
        message: The confirmation message to display
        show_options: Whether to show the y/n/q options
    
    Returns:
        bool: True if confirmed (y), False if declined (n), exits on q
    """
    if show_options:
        console.print(
            f"[bold yellow]{message} Press [green]y[/green] to confirm, [red]n[/red] to decline, or [blue]q[/blue] to quit:[/bold yellow] ",
            end=""
        )
    else:
        console.print(f"[bold yellow]{message}[/bold yellow] ", end="")
    
    while True:
        char = get_single_char().lower()
        
        if char == 'y':
            console.print("[green]y[/green]")
            console.print("✅ [green]Confirmed[/green]")
            return True
        elif char == 'n':
            console.print("[red]n[/red]")
            console.print("❌ [red]Declined[/red]")
            return False
        elif char == 'q':
            console.print("[blue]q[/blue]")
            console.print("🚪 [blue]Exiting...[/blue]")
            sys.exit(0)
        elif char == '\x03':  # Ctrl+C
            console.print("\n🛑 [red]Interrupted[/red]")
            raise KeyboardInterrupt
        else:
            # Invalid key, show the prompt again
            console.print(f"\n[red]Invalid key '[bold]{char}[/bold]'. Please press [green]y[/green], [red]n[/red], or [blue]q[/blue]:[/red] ", end="") 