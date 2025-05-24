#!/usr/bin/env python3
"""Demo script showcasing improved nlsh features"""

import sys
import os
sys.path.insert(0, 'src')

from nlsh.langgraph_llm import LangGraphLLMInterface
from nlsh.context import ContextManager
from nlsh.shell import ShellManager
from nlsh.utils import confirm_action

def demo_simple_confirmation():
    """Demonstrate the improved confirmation system"""
    print("=" * 60)
    print("🔧 DEMO: Simplified Confirmation System")
    print("=" * 60)
    print("✨ New features:")
    print("  - Simple y/n/q prompt with Enter")
    print("  - No more complex single-character input")
    print("  - Clear, user-friendly prompts")
    print()
    
    try:
        result1 = confirm_action("Try the first confirmation test?")
        print(f"First test result: {result1}")
        
        if result1:
            result2 = confirm_action("Try another confirmation?")
            print(f"Second test result: {result2}")
    except KeyboardInterrupt:
        print("User interrupted")

def demo_live_command_output():
    """Demonstrate live command output"""
    print("\n" + "=" * 60)
    print("🚀 DEMO: Live Command Output")
    print("=" * 60)
    print("✨ New features:")
    print("  - Real-time output display")
    print("  - No waiting for command completion")
    print("  - Full output shown immediately")
    print()
    
    shell_manager = ShellManager()
    
    # Demo commands that show the streaming effect
    commands = [
        ("echo 'This appears immediately'", "Simple output test"),
        ("ls -la | head -5", "Directory listing"),
        ("for i in {1..3}; do echo 'Line $i'; sleep 0.5; done", "Timed output test"),
        ("date", "Current date/time")
    ]
    
    for cmd, description in commands:
        print(f"\n🧪 {description}")
        print(f"Command: {cmd}")
        print("-" * 40)
        
        result = shell_manager.execute_command_with_live_output(cmd)
        
        print(f"\n📊 Result: Exit code {result.return_code}")
        if result.return_code != 0:
            print("❌ Command failed")
        else:
            print("✅ Command succeeded")

def demo_tool_execution():
    """Demonstrate LLM tool execution with streaming"""
    print("\n" + "=" * 60)
    print("🤖 DEMO: LLM Streaming with Tool Calls")
    print("=" * 60)
    print("✨ New features:")
    print("  - Real-time LLM response streaming")
    print("  - Animated tool call indicators")
    print("  - Live command execution")
    print()
    
    # Check if we have API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set - skipping LLM demo")
        print("   Set your OpenAI API key to see this demo")
        return
    
    try:
        # Setup components
        llm_interface = LangGraphLLMInterface()
        shell_manager = ShellManager()
        context_manager = ContextManager()
        
        llm_interface.setup_shell_integration(shell_manager)
        
        context = context_manager.get_context()
        shell_info = shell_manager.get_shell_info()
        context.shell_info = shell_info
        
        # Test prompt that should trigger tool calls
        prompt = "What's the current working directory and what files are in it?"
        
        print(f"🧪 Testing with prompt: '{prompt}'")
        print("-" * 40)
        
        response = llm_interface.generate_chat_response_streaming(prompt, context)
        
        print(f"\n📊 Final response length: {len(response)} characters")
        print("✅ LLM streaming demo completed")
        
    except Exception as e:
        print(f"❌ LLM demo error: {e}")

def main():
    print("🎯 NLSH IMPROVED FEATURES DEMONSTRATION")
    print("This demo shows the fixes for:")
    print("  1. ✅ Simple y/n confirmation prompts")
    print("  2. ✅ Real-time command output")
    print("  3. ✅ Proper LLM response streaming")
    print()
    
    try:
        demo_simple_confirmation()
        demo_live_command_output()
        demo_tool_execution()
        
        print("\n" + "=" * 60)
        print("🎉 DEMO COMPLETE!")
        print("=" * 60)
        print("Summary of improvements:")
        print("✅ Confirmation prompts are now simple and clear")
        print("✅ Command output appears in real-time")
        print("✅ No more truncated or delayed output")
        print("✅ LLM responses stream properly")
        print("✅ Tool calls have nice animated indicators")
        print()
        print("Try running the full nlsh tool to see everything in action!")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")

if __name__ == "__main__":
    main() 