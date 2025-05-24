#!/usr/bin/env python3
"""Debug script to test streaming functionality and identify issues"""

import sys
import traceback
sys.path.insert(0, 'src')

from nlsh.langgraph_llm import LangGraphLLMInterface
from nlsh.context import ContextManager
from nlsh.shell import ShellManager

def debug_streaming():
    """Debug the streaming functionality"""
    
    print("🔍 Debugging nlsh streaming functionality\n")
    
    try:
        # Test 1: Basic imports
        print("✅ Basic imports successful")
        
        # Test 2: Check if API key is available
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ No OPENAI_API_KEY found in environment")
            print("Please set your API key in .env file")
            return
        else:
            print(f"✅ API key found: {api_key[:8]}...")
        
        # Test 3: Initialize LangGraph interface
        print("\n🔧 Initializing LangGraph interface...")
        try:
            llm_interface = LangGraphLLMInterface()
            print("✅ LangGraph interface initialized")
        except Exception as e:
            print(f"❌ Failed to initialize LangGraph interface: {e}")
            traceback.print_exc()
            return
        
        # Test 4: Initialize context and shell
        print("\n🔧 Setting up context and shell...")
        try:
            shell_manager = ShellManager()
            context_manager = ContextManager()
            
            # Setup shell integration
            llm_interface.setup_shell_integration(shell_manager)
            print("✅ Shell integration set up")
            
            # Get context
            context = context_manager.get_context()
            shell_info = shell_manager.get_shell_info()
            context.shell_info = shell_info
            print("✅ Context prepared")
            
        except Exception as e:
            print(f"❌ Failed to set up context: {e}")
            traceback.print_exc()
            return
        
        # Test 5: Test non-streaming first
        print("\n🔧 Testing non-streaming chat response...")
        try:
            prompt = "What tools do you have?"
            response = llm_interface.generate_chat_response(prompt, context)
            print(f"✅ Non-streaming response: {response[:100]}...")
        except Exception as e:
            print(f"❌ Non-streaming failed: {e}")
            traceback.print_exc()
            return
        
        # Test 6: Test streaming
        print("\n🔧 Testing streaming chat response...")
        try:
            prompt = "What tools do you have?"
            print("Starting streaming response...")
            response = llm_interface.generate_chat_response_streaming(prompt, context)
            print(f"✅ Streaming response: {response[:100] if response else 'EMPTY RESPONSE'}...")
            
            if not response or not response.strip():
                print("❌ WARNING: Streaming returned empty response!")
                
        except Exception as e:
            print(f"❌ Streaming failed: {e}")
            traceback.print_exc()
            return
        
        # Test 7: Test graph streaming directly
        print("\n🔧 Testing graph.stream() directly...")
        try:
            from langchain_core.messages import HumanMessage
            
            initial_state = {
                "messages": [HumanMessage(content="What tools do you have?")],
                "context": context,
                "mode": "chat",
                "commands": []
            }
            
            print("Events from graph.stream():")
            event_count = 0
            for event in llm_interface.graph.stream(initial_state):
                event_count += 1
                print(f"Event {event_count}: {list(event.keys())}")
                for node_name, node_output in event.items():
                    print(f"  {node_name}: {type(node_output)}")
                    messages = node_output.get("messages", [])
                    print(f"    Messages count: {len(messages)}")
                    for i, msg in enumerate(messages):
                        print(f"      Message {i}: {type(msg)} - {getattr(msg, 'content', 'no content')[:50] if hasattr(msg, 'content') else 'no content attr'}...")
            
            print(f"Total events: {event_count}")
            
        except Exception as e:
            print(f"❌ Direct graph streaming failed: {e}")
            traceback.print_exc()
            return
        
        print("\n✅ Debug complete!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_streaming() 