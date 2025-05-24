#!/usr/bin/env python3
"""Test script to verify CLI fix for streaming display"""

import sys
sys.path.insert(0, 'src')

from nlsh.cli import handle_llm_chat
from nlsh.shell import ShellManager
from nlsh.context import ContextManager
from nlsh.history import HistoryManager
from nlsh.langgraph_llm import LangGraphLLMInterface

def test_cli_fix():
    """Test that the CLI fix displays streaming responses correctly"""
    
    print("🔧 Testing CLI streaming fix\n")
    
    try:
        # Initialize components like the main CLI does
        shell_manager = ShellManager()
        context_manager = ContextManager()
        history_manager = HistoryManager()
        
        llm_interface = LangGraphLLMInterface()
        llm_interface.setup_shell_integration(shell_manager)
        
        print("✅ Components initialized")
        
        # Test the handle_llm_chat function with streaming enabled
        print("\n🧪 Testing handle_llm_chat with streaming...")
        print("=" * 50)
        
        handle_llm_chat(
            prompt="What files are in the current directory?",
            shell_manager=shell_manager,
            context_manager=context_manager,
            history_manager=history_manager,
            llm_interface=llm_interface,
            use_langgraph=True,
            stream=True
        )
        
        print("\n✅ CLI streaming test complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cli_fix() 