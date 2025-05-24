#!/usr/bin/env python3
"""Test script to verify streaming with tool calls"""

import sys
sys.path.insert(0, 'src')

from nlsh.langgraph_llm import LangGraphLLMInterface
from nlsh.context import ContextManager
from nlsh.shell import ShellManager

def test_tool_streaming():
    """Test streaming with questions that should trigger tool calls"""
    
    print("🧪 Testing nlsh streaming with tool-triggering prompts\n")
    
    try:
        # Setup
        llm_interface = LangGraphLLMInterface()
        shell_manager = ShellManager()
        context_manager = ContextManager()
        
        llm_interface.setup_shell_integration(shell_manager)
        
        context = context_manager.get_context()
        shell_info = shell_manager.get_shell_info()
        context.shell_info = shell_info
        
        # Test prompts that should trigger tool calls
        test_prompts = [
            "What files are in the current directory?",
            "What's the current working directory?", 
            "Can you check the git status?",
            "What's in the README file?",
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🧪 Test {i}: {prompt}")
            print("=" * 50)
            
            try:
                response = llm_interface.generate_chat_response_streaming(prompt, context)
                print(f"\n✅ Response received: {len(response)} characters")
                print(f"Preview: {response[:100]}...")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n✅ Tool streaming test complete!")
        
    except Exception as e:
        print(f"❌ Setup error: {e}")

if __name__ == "__main__":
    test_tool_streaming() 