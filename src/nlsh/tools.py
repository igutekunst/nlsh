"""LangGraph tools for shell operations"""

import os
import subprocess
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .shell import ShellManager
from .context import ContextManager


class FileOperationInput(BaseModel):
    """Input for file operations"""
    path: str = Field(description="File or directory path")
    pattern: Optional[str] = Field(None, description="Search pattern (for find operations)")
    recursive: bool = Field(False, description="Whether to search recursively")


class ShellCommandInput(BaseModel):
    """Input for shell command execution"""
    command: str = Field(description="Shell command to execute")
    confirm: bool = Field(True, description="Whether to ask for confirmation before execution")


class GitOperationInput(BaseModel):
    """Input for git operations"""
    operation: str = Field(description="Git operation (status, log, diff, etc.)")
    args: Optional[str] = Field(None, description="Additional arguments")


@tool("list_files", args_schema=FileOperationInput)
def list_files_tool(path: str, pattern: Optional[str] = None, recursive: bool = False) -> str:
    """List files in a directory, optionally with pattern matching"""
    try:
        if not os.path.exists(path):
            return f"Path does not exist: {path}"
        
        if os.path.isfile(path):
            return f"File: {path}"
        
        files = []
        if recursive:
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    if pattern is None or pattern in filename:
                        files.append(os.path.join(root, filename))
        else:
            try:
                entries = os.listdir(path)
                for entry in entries:
                    full_path = os.path.join(path, entry)
                    if os.path.isfile(full_path):
                        if pattern is None or pattern in entry:
                            files.append(full_path)
            except PermissionError:
                return f"Permission denied: {path}"
        
        if not files:
            return f"No files found in {path}" + (f" matching '{pattern}'" if pattern else "")
        
        return "\n".join(files[:50])  # Limit to 50 files
        
    except Exception as e:
        return f"Error listing files: {e}"


@tool("read_file", args_schema=FileOperationInput)
def read_file_tool(path: str, **kwargs) -> str:
    """Read the contents of a file"""
    try:
        if not os.path.exists(path):
            return f"File does not exist: {path}"
        
        if not os.path.isfile(path):
            return f"Path is not a file: {path}"
        
        # Check file size
        file_size = os.path.getsize(path)
        if file_size > 1024 * 1024:  # 1MB limit
            return f"File too large to read: {path} ({file_size} bytes)"
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Truncate if too long
        if len(content) > 5000:
            content = content[:5000] + "\n... (file truncated)"
            
        return content
        
    except Exception as e:
        return f"Error reading file: {e}"


@tool("find_files", args_schema=FileOperationInput)
def find_files_tool(path: str, pattern: str, recursive: bool = True) -> str:
    """Find files matching a pattern"""
    try:
        shell_manager = ShellManager()
        
        if recursive:
            if shell_manager.detected_shell == 'fish':
                command = f"find {path} -name '*{pattern}*' 2>/dev/null"
            else:
                command = f"find {path} -name '*{pattern}*' 2>/dev/null"
        else:
            command = f"ls {path}/*{pattern}* 2>/dev/null || true"
        
        result = shell_manager.execute_command(command)
        
        if result.return_code == 0 and result.output.strip():
            return result.output.strip()
        else:
            return f"No files found matching '{pattern}' in {path}"
            
    except Exception as e:
        return f"Error finding files: {e}"


@tool("get_working_directory")
def get_working_directory_tool() -> str:
    """Get the current working directory"""
    return os.getcwd()


@tool("get_directory_tree", args_schema=FileOperationInput)
def get_directory_tree_tool(path: str, **kwargs) -> str:
    """Get a tree view of directory structure"""
    try:
        shell_manager = ShellManager()
        
        # Try tree command first, fallback to find
        tree_result = shell_manager.execute_command(f"tree -L 3 {path} 2>/dev/null")
        if tree_result.return_code == 0:
            return tree_result.output
        
        # Fallback to find
        find_result = shell_manager.execute_command(f"find {path} -maxdepth 3 -type d 2>/dev/null")
        if find_result.return_code == 0:
            return "Directory structure:\n" + find_result.output
        
        return f"Could not get directory tree for {path}"
        
    except Exception as e:
        return f"Error getting directory tree: {e}"


@tool("execute_shell_command", args_schema=ShellCommandInput)
def execute_shell_command_tool(command: str, confirm: bool = True) -> str:
    """Execute a shell command (with optional confirmation)"""
    try:
        # Note: This tool is for information gathering only
        # Actual command execution should be handled by the main CLI
        return f"Command ready for execution: {command}"
        
    except Exception as e:
        return f"Error preparing command: {e}"


@tool("git_status")
def git_status_tool() -> str:
    """Get git repository status"""
    try:
        shell_manager = ShellManager()
        result = shell_manager.execute_command("git status --porcelain")
        
        if result.return_code == 0:
            if not result.output.strip():
                return "Git repository is clean (no changes)"
            return f"Git status:\n{result.output}"
        else:
            return "Not a git repository or git not available"
            
    except Exception as e:
        return f"Error getting git status: {e}"


@tool("git_log", args_schema=GitOperationInput)
def git_log_tool(operation: str = "log", args: Optional[str] = None) -> str:
    """Get git log information"""
    try:
        shell_manager = ShellManager()
        
        if args:
            command = f"git log {args}"
        else:
            command = "git log --oneline -10"  # Last 10 commits
        
        result = shell_manager.execute_command(command)
        
        if result.return_code == 0:
            return f"Git log:\n{result.output}"
        else:
            return "Error getting git log or not a git repository"
            
    except Exception as e:
        return f"Error getting git log: {e}"


@tool("get_system_info")
def get_system_info_tool() -> str:
    """Get system information"""
    try:
        context_manager = ContextManager()
        context = context_manager.get_context()
        
        info = f"""System Information:
- Platform: {context.system_info['platform']} {context.system_info['platform_release']}
- Architecture: {context.system_info['architecture']}
- Python: {context.system_info['python_version']}
- Current Directory: {context.cwd}
- Shell: {context.shell_info.get('name', 'unknown')}

Environment:
"""
        for key, value in list(context.environment.items())[:5]:
            info += f"- {key}: {value}\n"
        
        return info
        
    except Exception as e:
        return f"Error getting system info: {e}"


@tool("get_file_info", args_schema=FileOperationInput)
def get_file_info_tool(path: str, **kwargs) -> str:
    """Get detailed information about a file or directory"""
    try:
        if not os.path.exists(path):
            return f"Path does not exist: {path}"
        
        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        
        info = f"Path: {path}\n"
        info += f"Type: {'Directory' if is_dir else 'File'}\n"
        info += f"Size: {stat.st_size} bytes\n"
        info += f"Modified: {stat.st_mtime}\n"
        
        if is_dir:
            try:
                entries = os.listdir(path)
                info += f"Contains: {len(entries)} items\n"
            except PermissionError:
                info += "Contents: Permission denied\n"
        
        return info
        
    except Exception as e:
        return f"Error getting file info: {e}"


# Export all tools for LangGraph
AVAILABLE_TOOLS = [
    list_files_tool,
    read_file_tool,
    find_files_tool,
    get_working_directory_tool,
    get_directory_tree_tool,
    execute_shell_command_tool,
    git_status_tool,
    git_log_tool,
    get_system_info_tool,
    get_file_info_tool
] 