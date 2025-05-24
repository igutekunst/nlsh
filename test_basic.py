#!/usr/bin/env python3
"""Basic functionality test for nlsh without requiring API keys"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, 'src')

from nlsh.shell import ShellManager
from nlsh.context import ContextManager
from nlsh.history import HistoryManager


def test_shell_detection():
    """Test shell detection functionality"""
    print("Testing shell detection...")
    shell_manager = ShellManager()
    
    print(f"Detected shell: {shell_manager.detected_shell}")
    print(f"Shell path: {shell_manager.get_shell_path()}")
    
    shell_info = shell_manager.get_shell_info()
    print(f"Shell info: {shell_info}")
    
    # Test basic command execution
    result = shell_manager.execute_command("echo 'Hello from nlsh test'")
    print(f"Test command result: {result.output.strip()}")
    assert result.return_code == 0
    assert "Hello from nlsh test" in result.output
    print("✓ Shell detection and execution working")


def test_context_gathering():
    """Test context gathering functionality"""
    print("\nTesting context gathering...")
    context_manager = ContextManager()
    
    context = context_manager.get_context()
    print(f"Current directory: {context.cwd}")
    print(f"Shell info: {context.shell_info}")
    print(f"System info: {context.system_info}")
    print(f"Environment vars count: {len(context.environment)}")
    print(f"Filesystem entries: {len(context.filesystem)}")
    
    # Test context formatting
    formatted = context_manager.format_context_for_llm(context)
    assert "Working Directory:" in formatted
    assert "Shell Information:" in formatted
    print("✓ Context gathering working")


def test_history_management():
    """Test SQLite history functionality"""
    print("\nTesting history management...")
    
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db = tmp.name
    
    try:
        history_manager = HistoryManager(db_path=tmp_db)
        
        # Test shell command logging
        from nlsh.shell import CommandResult
        test_result = CommandResult(
            command="echo test",
            output="test\n",
            error="",
            return_code=0,
            cwd=os.getcwd()
        )
        
        history_manager.log_shell_command("echo test", test_result)
        
        # Test retrieving history
        recent = history_manager.get_recent_commands(limit=5)
        print(f"Recent commands count: {len(recent)}")
        assert len(recent) >= 1
        
        # Test stats
        stats = history_manager.get_command_stats()
        print(f"History stats: {stats}")
        assert stats['total_entries'] >= 1
        
        print("✓ History management working")
        
    finally:
        # Clean up temporary database
        if os.path.exists(tmp_db):
            os.unlink(tmp_db)


def test_file_structure():
    """Test that all required files exist"""
    print("\nTesting file structure...")
    
    required_files = [
        'src/nlsh/__init__.py',
        'src/nlsh/cli.py',
        'src/nlsh/shell.py',
        'src/nlsh/context.py',
        'src/nlsh/history.py',
        'src/nlsh/llm.py',
        'pyproject.toml',
        'README.md',
        '.env.example'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"✗ Missing required file: {file_path}")
            return False
        
    print("✓ All required files present")
    return True


def main():
    """Run all tests"""
    print("Running nlsh basic functionality tests...\n")
    
    try:
        test_file_structure()
        test_shell_detection()
        test_context_gathering()
        test_history_management()
        
        print("\n🎉 All basic tests passed!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your OpenAI API key to .env")
        print("3. Run: nlsh")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 