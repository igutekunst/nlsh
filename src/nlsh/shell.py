"""Shell command execution and management"""

import os
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    """Result of executing a shell command"""
    command: str
    output: str
    error: str
    return_code: int
    cwd: str


class ShellManager:
    """Manages shell detection and command execution"""
    
    def __init__(self):
        self.detected_shell = self._detect_shell()
        
    def _detect_shell(self) -> str:
        """Detect the user's current shell"""
        # Try to get shell from environment
        shell_path = os.environ.get('SHELL', '/bin/bash')
        
        # Extract shell name from path
        shell_name = os.path.basename(shell_path)
        
        # Validate that the shell exists
        if shutil.which(shell_path):
            return shell_name
        
        # Fallback to common shells
        for shell in ['bash', 'zsh', 'fish', 'sh']:
            if shutil.which(shell):
                return shell
                
        return 'sh'  # Ultimate fallback
    
    def get_shell_path(self) -> str:
        """Get the full path to the detected shell"""
        shell_path = os.environ.get('SHELL')
        if shell_path and shutil.which(shell_path):
            return shell_path
            
        # Try to find the shell in PATH
        shell_path = shutil.which(self.detected_shell)
        if shell_path:
            return shell_path
            
        return '/bin/sh'  # Fallback
    
    def execute_command(self, command: str) -> CommandResult:
        """Execute a command in the detected shell"""
        cwd = os.getcwd()
        shell_path = self.get_shell_path()
        
        try:
            # Execute command through the user's shell
            if self.detected_shell == 'fish':
                # Fish shell needs special handling
                result = subprocess.run(
                    [shell_path, '-c', command],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=30  # 30 second timeout
                )
            else:
                # Most shells (bash, zsh, sh) use -c flag
                result = subprocess.run(
                    [shell_path, '-c', command],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=30
                )
            
            return CommandResult(
                command=command,
                output=result.stdout,
                error=result.stderr,
                return_code=result.returncode,
                cwd=cwd
            )
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                output="",
                error="Command timed out after 30 seconds",
                return_code=-1,
                cwd=cwd
            )
        except Exception as e:
            return CommandResult(
                command=command,
                output="",
                error=f"Failed to execute command: {e}",
                return_code=-1,
                cwd=cwd
            )
    
    def get_shell_info(self) -> dict:
        """Get information about the detected shell for LLM context"""
        return {
            'name': self.detected_shell,
            'path': self.get_shell_path(),
            'version': self._get_shell_version(),
            'features': self._get_shell_features()
        }
    
    def _get_shell_version(self) -> str:
        """Get the version of the detected shell"""
        try:
            version_commands = {
                'bash': '--version',
                'zsh': '--version', 
                'fish': '--version',
                'sh': '--version'
            }
            
            version_flag = version_commands.get(self.detected_shell, '--version')
            result = subprocess.run(
                [self.get_shell_path(), version_flag],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract first line which usually contains version
                return result.stdout.split('\n')[0].strip()
            
        except Exception:
            pass
        
        return "unknown"
    
    def _get_shell_features(self) -> dict:
        """Get shell-specific features for LLM context"""
        features = {
            'bash': {
                'syntax': 'bash',
                'supports_arrays': True,
                'supports_functions': True,
                'variable_syntax': '$VAR',
                'pipe_operator': '|'
            },
            'zsh': {
                'syntax': 'zsh', 
                'supports_arrays': True,
                'supports_functions': True,
                'supports_glob_expansion': True,
                'variable_syntax': '$VAR',
                'pipe_operator': '|'
            },
            'fish': {
                'syntax': 'fish',
                'supports_arrays': True,
                'supports_functions': True,
                'variable_syntax': '$VAR',
                'pipe_operator': '|',
                'special_features': ['abbreviations', 'autosuggestions']
            },
            'sh': {
                'syntax': 'sh',
                'supports_arrays': False,
                'supports_functions': True,
                'variable_syntax': '$VAR',
                'pipe_operator': '|'
            }
        }
        
        return features.get(self.detected_shell, features['sh']) 