#!/usr/bin/env python3
"""Test script to verify improved streaming and confirmation"""

import sys
sys.path.insert(0, 'src')

from nlsh.shell import ShellManager
from nlsh.utils import confirm_action

def test_simple_confirmation():
    """Test the simplified confirmation prompt"""
    print("🧪 Testing simplified confirmation prompt\n")
    
    print("This should show a simple y/n/q prompt:")
    try:
        result = confirm_action("Test the new confirmation system?")
        print(f"Result: {result}")
    except KeyboardInterrupt:
        print("Interrupted by user")

def test_live_command_output():
    """Test live command output"""
    print("\n🧪 Testing live command output\n")
    
    shell_manager = ShellManager()
    
    # Test commands that produce output
    test_commands = [
        "echo 'Testing live output'",
        "ls -la",
        "date",
        "echo 'Line 1'; sleep 1; echo 'Line 2'; sleep 1; echo 'Line 3'"
    ]
    
    for cmd in test_commands:
        print(f"\n[TESTING] Command: {cmd}")
        print("-" * 40)
        result = shell_manager.execute_command_with_live_output(cmd)
        print(f"\n[RESULT] Exit code: {result.return_code}")
        if result.return_code != 0:
            print(f"[ERROR] Command failed")

def main():
    print("🚀 Testing improved nlsh streaming and confirmation\n")
    
    try:
        test_simple_confirmation()
        test_live_command_output()
        print("\n✅ All tests completed!")
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    main() 