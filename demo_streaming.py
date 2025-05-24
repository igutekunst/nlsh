#!/usr/bin/env python3
"""Demo script to show streaming interface functionality"""

import time
import sys
sys.path.insert(0, 'src')

from nlsh.streaming import create_streaming_interface

def demo_streaming():
    """Demonstrate the streaming interface with animated spinners"""
    
    print("🎬 nlsh Streaming Interface Demo\n")
    
    # Create streaming interface
    streaming_response, confirmation_handler = create_streaming_interface()
    
    # Demo various tool calls
    tools_demo = [
        ("list_files", {"path": "/home/user/projects"}),
        ("read_file", {"path": "config.py"}),
        ("find_files", {"pattern": "*.py", "path": "."}),
        ("git_status", {}),
        ("execute_shell_command", {"command": "ls -la"}),
        ("get_system_info", {}),
    ]
    
    print("Demonstrating tool calls with animated spinners:\n")
    
    for tool_name, args in tools_demo:
        # Start tool call animation
        streaming_response.start_tool_call(tool_name, args)
        
        # Simulate tool execution time
        time.sleep(2)
        
        # Finish with a result
        sample_results = {
            "list_files": "file1.py\nfile2.py\nREADME.md",
            "read_file": "# Configuration\napi_key = 'your_key_here'\ndebug = True",
            "find_files": "./main.py\n./utils.py\n./tests/test_main.py",
            "git_status": "On branch main\nnothing to commit, working tree clean",
            "execute_shell_command": "total 8\ndrwxr-xr-x  4 user user 128 Nov 15 10:30 .",
            "get_system_info": "Platform: Darwin 23.4.0\nArchitecture: arm64\nPython: 3.11.0"
        }
        
        result = sample_results.get(tool_name, "Tool completed successfully")
        streaming_response.finish_tool_call(result)
        
        # Brief pause between tools
        time.sleep(0.5)
    
    print("\n🎯 Demo of confirmation handler:")
    
    # Demo confirmation
    sample_commands = [
        "git status",
        "find . -name '*.py' -type f",
        "rm -rf /important/data"  # This one should be scary!
    ]
    
    for cmd in sample_commands:
        print(f"\nTesting confirmation for: {cmd}")
        try:
            confirmed = confirmation_handler.request_confirmation(cmd)
            if confirmed:
                print("✅ User confirmed - would execute command")
            else:
                print("❌ User cancelled - command not executed")
        except KeyboardInterrupt:
            print("⏹️  User interrupted")
            break
        except Exception as e:
            print(f"Note: {e} (expected in demo)")
    
    print("\n✨ Demo complete! This is what you'll see when using nlsh with streaming enabled.")
    print("🚀 Run 'nlsh' to try it with real AI!")

if __name__ == "__main__":
    demo_streaming() 