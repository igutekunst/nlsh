#!/usr/bin/env python3
"""Test the streaming fix"""

import sys
sys.path.insert(0, 'src')

from nlsh.langgraph_llm import LangGraphLLMInterface
from nlsh.context import ContextManager
from nlsh.shell import ShellManager

def test_streaming_fix():
    """Test that the LLM captures tool results correctly"""
    
    try:
        # Setup
        llm = LangGraphLLMInterface()
        shell = ShellManager()
        context_mgr = ContextManager()
        
        llm.setup_shell_integration(shell)
        context = context_mgr.get_context()
        context.shell_info = shell.get_shell_info()
        
        # Test with a simple command that should show actual output
        prompt = "what is my ip address?"
        print(f"Testing with prompt: '{prompt}'")
        print("=" * 50)
        
        response = llm.generate_chat_response_streaming(prompt, context)
        
        print("\n" + "=" * 50)
        print("FINAL RESPONSE:")
        print(repr(response))
        print("\nResponse content:")
        print(response)
        print("=" * 50)
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_streaming_fix() 