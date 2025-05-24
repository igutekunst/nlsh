#!/usr/bin/env python3
"""Test script to verify LLM provider selection logic"""

import os
import sys
sys.path.insert(0, 'src')

def test_provider_selection():
    """Test that provider selection works correctly"""
    
    print("🧪 Testing LLM provider selection logic\n")
    
    # Store original values
    original_anthropic = os.environ.get('ANTHROPIC_API_KEY')
    original_openai = os.environ.get('OPENAI_API_KEY')
    
    try:
        # Test 1: Both keys available (should prefer Anthropic)
        print("Test 1: Both API keys available")
        os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
        os.environ['OPENAI_API_KEY'] = 'test_openai_key'
        
        try:
            from src.nlsh.langgraph_llm import LangGraphLLMInterface
            # Clear module cache to get fresh import
            if 'src.nlsh.langgraph_llm' in sys.modules:
                del sys.modules['src.nlsh.langgraph_llm']
            
            from src.nlsh.langgraph_llm import LangGraphLLMInterface
            llm = LangGraphLLMInterface()
            
            if llm.provider == "anthropic":
                print("✅ Correctly chose Anthropic when both keys available")
            else:
                print(f"❌ Expected Anthropic, got {llm.provider}")
                
        except Exception as e:
            if "ANTHROPIC_AVAILABLE" in str(e) or "langchain-anthropic" in str(e):
                print("⚠️  Anthropic not installed - this is expected if langchain-anthropic is not available")
                print("   Install with: pip install langchain-anthropic")
            else:
                print(f"❌ Unexpected error: {e}")
        
        # Test 2: Only OpenAI key (should use OpenAI)
        print("\nTest 2: Only OpenAI API key available")
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ['OPENAI_API_KEY'] = 'test_openai_key'
        
        # Clear module cache
        if 'src.nlsh.langgraph_llm' in sys.modules:
            del sys.modules['src.nlsh.langgraph_llm']
        
        try:
            from src.nlsh.langgraph_llm import LangGraphLLMInterface
            llm = LangGraphLLMInterface()
            
            if llm.provider == "openai":
                print("✅ Correctly chose OpenAI when only OpenAI key available")
            else:
                print(f"❌ Expected OpenAI, got {llm.provider}")
                
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Test 3: No keys (should fail)
        print("\nTest 3: No API keys available")
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('OPENAI_API_KEY', None)
        
        # Clear module cache
        if 'src.nlsh.langgraph_llm' in sys.modules:
            del sys.modules['src.nlsh.langgraph_llm']
        
        try:
            from src.nlsh.langgraph_llm import LangGraphLLMInterface
            llm = LangGraphLLMInterface()
            print("❌ Should have failed without any API keys")
        except ValueError as e:
            if "No valid API key found" in str(e):
                print("✅ Correctly failed when no API keys available")
            else:
                print(f"❌ Wrong error message: {e}")
        except Exception as e:
            print(f"❌ Unexpected error type: {e}")
    
    finally:
        # Restore original values
        if original_anthropic:
            os.environ['ANTHROPIC_API_KEY'] = original_anthropic
        else:
            os.environ.pop('ANTHROPIC_API_KEY', None)
            
        if original_openai:
            os.environ['OPENAI_API_KEY'] = original_openai
        else:
            os.environ.pop('OPENAI_API_KEY', None)
    
    print("\n✅ Provider selection testing complete!")

if __name__ == "__main__":
    test_provider_selection() 