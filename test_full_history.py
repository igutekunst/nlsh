#!/usr/bin/env python3
"""Test comprehensive session history integration"""

import tempfile
import os
from src.nlsh.context import ContextManager
from src.nlsh.history import HistoryManager
from src.nlsh.shell import CommandResult

def test_comprehensive_history():
    """Test that all interaction types are logged and included in context"""
    
    # Create temporary history database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize managers
        history_manager = HistoryManager(db_path)
        context_manager = ContextManager()
        
        print("📝 Logging comprehensive session history...")
        
        # 1. Log a shell command
        shell_result = CommandResult(
            command="ls -la",
            output="total 24\ndrwxr-xr-x  5 user user 4096 Jan 1 12:00 .\ndrwxr-xr-x  3 user user 4096 Jan 1 11:00 ..\n-rw-r--r--  1 user user   42 Jan 1 12:00 test.py",
            error="",
            return_code=0,
            cwd="/test/dir"
        )
        history_manager.log_shell_command("ls -la", shell_result)
        
        # 2. Log an LLM interaction with response and tool calls
        interaction_id = history_manager.log_llm_interaction(
            user_prompt="What files are in the current directory?",
            llm_response="I can see there are several files in the current directory including test.py. Let me get more details.",
            generated_commands=[],
            executed_commands=[],
            execution_results=[],
            llm_model="gpt-4o-mini"
        )
        
        # 3. Log some tool calls for this interaction
        history_manager.log_tool_call(
            tool_name="list_files",
            tool_args={"path": ".", "recursive": False},
            tool_result="Found 3 files: test.py, config.json, README.md"
        )
        
        history_manager.log_tool_call(
            tool_name="read_file",
            tool_args={"path": "test.py"},
            tool_result="print('Hello World')\n# This is a test file"
        )
        
        # 4. Log another shell command
        error_result = CommandResult(
            command="invalid_command",
            output="",
            error="command not found: invalid_command",
            return_code=127,
            cwd="/test/dir"
        )
        history_manager.log_shell_command("invalid_command", error_result)
        
        # 5. Log another LLM interaction with commands
        history_manager.log_llm_interaction(
            user_prompt="Show me the content of all Python files",
            llm_response="Generated 2 command(s)",
            generated_commands=["find . -name '*.py'", "cat *.py"],
            executed_commands=["find . -name '*.py'"],
            execution_results=[CommandResult(
                command="find . -name '*.py'",
                output="./test.py\n./script.py",
                error="",
                return_code=0,
                cwd="/test/dir"
            )],
            llm_model="gpt-4o-mini"
        )
        
        # Now get context with history and verify everything is included
        print("\n📊 Getting context with comprehensive history...")
        context_with_history = context_manager.get_context(history_manager)
        formatted_context = context_manager.format_context_for_llm(context_with_history)
        
        print("\n" + "="*80)
        print("COMPREHENSIVE SESSION HISTORY CONTEXT:")
        print("="*80)
        print(formatted_context)
        print("="*80)
        
        # Verify all types are included
        history_section = formatted_context.split("Session History (Recent Activity):")[1].split("System Information:")[0]
        
        checks = {
            "shell_command": "Manual:" in history_section,
            "llm_interaction": "User:" in history_section and "AI:" in history_section,
            "tool_calls": "Tool:" in history_section,
            "failed_command": "❌" in history_section,
            "successful_command": "✅" in history_section,
            "generated_commands": "Generated" in history_section,
            "executed_commands": "Executed:" in history_section
        }
        
        print(f"\n📋 Verification Results:")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}: {passed}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All session history integration tests passed!")
            print("   The LLM now has complete context of:")
            print("   - Manual shell commands and their results")
            print("   - User questions and AI responses")
            print("   - Tool calls made by the AI")
            print("   - Command generation and execution")
            print("   - Success/failure status of all actions")
            return True
        else:
            print("\n❌ Some tests failed - check the implementation")
            return False
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    print("🧪 Testing comprehensive session history integration...")
    success = test_comprehensive_history()
    exit(0 if success else 1) 