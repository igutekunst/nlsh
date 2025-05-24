"""Context management for filesystem and environment state"""

import os
import platform
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a file or directory"""
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: Optional[float] = None


@dataclass
class ContextInfo:
    """Complete context information for LLM"""
    cwd: str
    shell_info: dict
    filesystem: Dict[str, List[FileInfo]]
    environment: dict
    system_info: dict
    session_history: Optional[List[Dict]] = None


class ContextManager:
    """Manages context information for LLM requests"""
    
    def __init__(self, max_depth: int = 3, max_files_per_dir: int = 50):
        self.max_depth = max_depth
        self.max_files_per_dir = max_files_per_dir
        
    def get_context(self, history_manager=None) -> ContextInfo:
        """Get complete context information"""
        cwd = os.getcwd()
        
        # Get session history if history_manager is provided
        session_history = None
        if history_manager:
            session_history = self._get_session_history(history_manager)
        
        return ContextInfo(
            cwd=cwd,
            shell_info=self._get_shell_context(),
            filesystem=self._get_filesystem_context(cwd),
            environment=self._get_environment_context(),
            system_info=self._get_system_context(),
            session_history=session_history
        )
    
    def _get_session_history(self, history_manager, limit: int = 15) -> List[Dict]:
        """Get formatted session history for context"""
        try:
            # Get recent entries from current session
            entries = history_manager.get_session_history()
            
            # Limit to recent entries and format for context
            recent_entries = entries[-limit:] if len(entries) > limit else entries
            
            formatted_history = []
            for entry in recent_entries:
                entry_data = entry.get('data', {})
                
                if entry['entry_type'] == 'shell_command':
                    formatted_entry = {
                        'type': 'shell_command',
                        'timestamp': entry['timestamp'],
                        'command': entry_data.get('command', ''),
                        'success': entry_data.get('return_code', 0) == 0,
                        'output_summary': self._truncate_text(entry_data.get('output', ''), 200)
                    }
                elif entry['entry_type'] == 'llm_interaction':
                    formatted_entry = {
                        'type': 'llm_interaction', 
                        'timestamp': entry['timestamp'],
                        'user_prompt': entry_data.get('user_prompt', ''),
                        'llm_response': self._truncate_text(entry_data.get('llm_response', ''), 300),
                        'generated_commands': entry_data.get('generated_commands', []),
                        'executed_commands': entry_data.get('executed_commands', [])
                    }
                elif entry['entry_type'] == 'tool_call':
                    formatted_entry = {
                        'type': 'tool_call',
                        'timestamp': entry['timestamp'],
                        'tool_name': entry_data.get('tool_name', ''),
                        'tool_args': entry_data.get('tool_args', {}),
                        'tool_result': self._truncate_text(entry_data.get('tool_result', ''), 150)
                    }
                else:
                    continue  # Skip other entry types for now
                    
                formatted_history.append(formatted_entry)
                
            return formatted_history
            
        except Exception:
            # If history retrieval fails, return empty list
            return []
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length with ellipsis"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _get_shell_context(self) -> dict:
        """Get shell-specific context (will be populated by ShellManager)"""
        # This will be enhanced when called with shell_manager.get_shell_info()
        return {
            'name': os.environ.get('SHELL', '').split('/')[-1] or 'unknown',
            'path': os.environ.get('SHELL', ''),
        }
    
    def _get_filesystem_context(self, root_path: str) -> Dict[str, List[FileInfo]]:
        """Get recursive filesystem context with depth limits"""
        filesystem = {}
        
        try:
            # Scan current directory and subdirectories
            for current_depth in range(self.max_depth + 1):
                if current_depth == 0:
                    # Current directory
                    path_key = "."
                    scan_path = root_path
                else:
                    # Skip deeper directories for now - implement recursive scanning
                    continue
                    
                filesystem[path_key] = self._scan_directory(scan_path)
                
            # Also scan immediate subdirectories
            try:
                current_files = filesystem.get(".", [])
                subdirs = [f for f in current_files if f.is_dir]
                
                for subdir in subdirs[:10]:  # Limit to first 10 subdirectories
                    subdir_path = os.path.join(root_path, subdir.name)
                    rel_path = f"./{subdir.name}"
                    filesystem[rel_path] = self._scan_directory(subdir_path, depth=1)
                    
            except Exception:
                pass  # Continue if subdirectory scanning fails
                
        except Exception as e:
            # If filesystem scanning fails, at least provide current directory info
            filesystem["."] = []
            
        return filesystem
    
    def _scan_directory(self, path: str, depth: int = 0) -> List[FileInfo]:
        """Scan a single directory and return file information"""
        files = []
        
        try:
            # Don't scan if we're at max depth
            if depth >= self.max_depth:
                return files
                
            entries = list(os.listdir(path))
            
            # Sort entries: directories first, then files, both alphabetically
            entries.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            
            # Limit number of files to prevent overwhelming context
            entries = entries[:self.max_files_per_dir]
            
            for entry in entries:
                try:
                    entry_path = os.path.join(path, entry)
                    stat_info = os.stat(entry_path)
                    
                    is_dir = os.path.isdir(entry_path)
                    
                    files.append(FileInfo(
                        name=entry,
                        path=entry_path,
                        is_dir=is_dir,
                        size=None if is_dir else stat_info.st_size,
                        modified=stat_info.st_mtime
                    ))
                    
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
                    
        except (OSError, PermissionError):
            # Return empty list if we can't read the directory
            pass
            
        return files
    
    def _get_environment_context(self) -> dict:
        """Get relevant environment variables"""
        # Include common environment variables that might be useful
        relevant_vars = [
            'PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'LANG',
            'PWD', 'OLDPWD', 'PS1', 'EDITOR', 'PAGER'
        ]
        
        env_context = {}
        for var in relevant_vars:
            value = os.environ.get(var)
            if value:
                env_context[var] = value
                
        return env_context
    
    def _get_system_context(self) -> dict:
        """Get system information"""
        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
        }
    
    def format_context_for_llm(self, context: ContextInfo, shell_info: dict = None) -> str:
        """Format context information for LLM consumption"""
        # Override shell_info if provided (from ShellManager)
        if shell_info:
            context.shell_info = shell_info
            
        context_str = f"""Current Context:

Working Directory: {context.cwd}

Shell Information:
- Name: {context.shell_info.get('name', 'unknown')}
- Path: {context.shell_info.get('path', 'unknown')}
- Version: {context.shell_info.get('version', 'unknown')}

Filesystem Context:
"""
        
        # Add filesystem information
        for path, files in context.filesystem.items():
            if not files:
                continue
                
            context_str += f"\n{path}/:\n"
            
            # Group by directories and files
            dirs = [f for f in files if f.is_dir]
            regular_files = [f for f in files if not f.is_dir]
            
            # Show directories first
            for d in dirs[:10]:  # Limit output
                context_str += f"  📁 {d.name}/\n"
                
            # Show files
            for f in regular_files[:15]:  # Limit output
                size_str = f" ({self._format_size(f.size)})" if f.size else ""
                context_str += f"  📄 {f.name}{size_str}\n"
                
            if len(files) > 25:
                context_str += f"  ... and {len(files) - 25} more items\n"
        
        # Add session history if available
        if context.session_history:
            context_str += "\nSession History (Recent Activity):\n"
            for i, entry in enumerate(context.session_history, 1):
                if entry['type'] == 'shell_command':
                    success_indicator = "✅" if entry['success'] else "❌"
                    context_str += f"  {i}. {success_indicator} Manual: {entry['command']}"
                    if entry['output_summary']:
                        context_str += f" -> {entry['output_summary']}"
                    context_str += "\n"
                elif entry['type'] == 'llm_interaction':
                    context_str += f"  {i}. 💬 User: \"{entry['user_prompt']}\"\n"
                    if entry['llm_response']:
                        context_str += f"      AI: {entry['llm_response']}\n"
                    if entry['executed_commands']:
                        context_str += f"      ✅ Executed: {', '.join(entry['executed_commands'])}\n"
                    elif entry['generated_commands']:
                        context_str += f"      💡 Suggested: {', '.join(entry['generated_commands'])}\n"
                elif entry['type'] == 'tool_call':
                    tool_args_str = ', '.join([f"{k}={v}" for k, v in list(entry['tool_args'].items())[:2]])
                    if len(entry['tool_args']) > 2:
                        tool_args_str += "..."
                    context_str += f"  {i}. 🔧 Tool: {entry['tool_name']}({tool_args_str})"
                    if entry['tool_result']:
                        context_str += f" -> {entry['tool_result']}"
                    context_str += "\n"
        
        # Add system context
        context_str += f"""
System Information:
- Platform: {context.system_info['platform']} {context.system_info['platform_release']}
- Architecture: {context.system_info['architecture']}

Environment Variables:
"""
        
        # Add key environment variables
        for key, value in list(context.environment.items())[:8]:
            # Truncate long values
            display_value = value if len(value) < 100 else value[:97] + "..."
            context_str += f"- {key}: {display_value}\n"
            
        return context_str
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes // 1024}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes // (1024 * 1024)}MB"
        else:
            return f"{size_bytes // (1024 * 1024 * 1024)}GB" 