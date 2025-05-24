"""Utility functions for nlsh"""

import sys
from rich.console import Console

console = Console()


def confirm_action(message: str = "Continue?") -> bool:
    """
    Get confirmation with simple y/n input followed by Enter
    
    Args:
        message: The confirmation message to display
    
    Returns:
        bool: True if confirmed (y), False if declined (n), exits on q
    """
    while True:
        try:
            console.print(f"[bold yellow]{message} (y/n/q):[/bold yellow] ", end="")
            response = input().strip().lower()
            
            if response in ['y', 'yes']:
                console.print("✅ [green]Confirmed[/green]")
                return True
            elif response in ['n', 'no']:
                console.print("❌ [red]Declined[/red]")
                return False
            elif response in ['q', 'quit']:
                console.print("🚪 [blue]Exiting...[/blue]")
                sys.exit(0)
            else:
                console.print("[red]Please enter 'y' for yes, 'n' for no, or 'q' to quit.[/red]")
        except KeyboardInterrupt:
            console.print("\n🛑 [red]Interrupted[/red]")
            raise KeyboardInterrupt
        except EOFError:
            console.print("\n🚪 [blue]Exiting...[/blue]")
            sys.exit(0) 