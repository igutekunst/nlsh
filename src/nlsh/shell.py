"""Shell command execution and management"""

import os
import subprocess
import shutil
import asyncio
import sys
from dataclasses import dataclass
from typing import Optional, Iterator, AsyncIterator


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

    async def execute_command_streaming(self, command: str) -> AsyncIterator[tuple[str, str]]:
        """
        Execute a command with streaming output.
        
        Yields:
            tuple[str, str]: (stream_type, content) where stream_type is 'stdout', 'stderr', or 'exit'
        """
        cwd = os.getcwd()
        shell_path = self.get_shell_path()
        
        try:
            # Create subprocess with pipes for real-time output
            if self.detected_shell == 'fish':
                proc = await asyncio.create_subprocess_exec(
                    shell_path, '-c', command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    shell_path, '-c', command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
            
            # Stream output in real-time
            async def read_stream(stream, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    yield (stream_type, line.decode('utf-8', errors='replace'))
            
            # Create tasks for reading both stdout and stderr
            stdout_task = asyncio.create_task(
                self._collect_stream_output(read_stream(proc.stdout, 'stdout'))
            )
            stderr_task = asyncio.create_task(
                self._collect_stream_output(read_stream(proc.stderr, 'stderr'))
            )
            
            # Yield output as it comes
            while not proc.returncode and (not stdout_task.done() or not stderr_task.done()):
                if not stdout_task.done():
                    try:
                        stream_type, content = await asyncio.wait_for(stdout_task, timeout=0.1)
                        yield (stream_type, content)
                        stdout_task = asyncio.create_task(
                            self._collect_stream_output(read_stream(proc.stdout, 'stdout'))
                        )
                    except asyncio.TimeoutError:
                        pass
                
                if not stderr_task.done():
                    try:
                        stream_type, content = await asyncio.wait_for(stderr_task, timeout=0.1)
                        yield (stream_type, content)
                        stderr_task = asyncio.create_task(
                            self._collect_stream_output(read_stream(proc.stderr, 'stderr'))
                        )
                    except asyncio.TimeoutError:
                        pass
                
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
            
            # Wait for process to complete
            await proc.wait()
            
            # Cancel any remaining tasks
            stdout_task.cancel()
            stderr_task.cancel()
            
            # Yield exit code
            yield ('exit', str(proc.returncode))
            
        except Exception as e:
            yield ('stderr', f"Failed to execute command: {e}\n")
            yield ('exit', '-1')

    async def _collect_stream_output(self, stream_generator):
        """Helper to collect single output from stream generator"""
        async for stream_type, content in stream_generator:
            return (stream_type, content)
        return None
    
    def execute_command_with_live_output(self, command: str) -> CommandResult:
        """
        Execute a command with live output displayed to console.
        Returns the complete result after execution.
        """
        cwd = os.getcwd()
        shell_path = self.get_shell_path()
        
        try:
            # Execute command with real-time output
            if self.detected_shell == 'fish':
                proc = subprocess.Popen(
                    [shell_path, '-c', command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=cwd,
                    bufsize=1,  # Line buffering
                    universal_newlines=True
                )
            else:
                proc = subprocess.Popen(
                    [shell_path, '-c', command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=cwd,
                    bufsize=1,  # Line buffering
                    universal_newlines=True
                )
            
            stdout_lines = []
            stderr_lines = []
            
            # Read and display output in real-time
            while True:
                # Check if process is still running
                if proc.poll() is not None:
                    break
                
                # Read stdout if available
                if proc.stdout:
                    line = proc.stdout.readline()
                    if line:
                        print(line, end='', flush=True)
                        stdout_lines.append(line)
                
                # Read stderr if available  
                if proc.stderr:
                    line = proc.stderr.readline()
                    if line:
                        print(line, end='', file=sys.stderr, flush=True)
                        stderr_lines.append(line)
            
            # Get any remaining output
            remaining_stdout, remaining_stderr = proc.communicate()
            if remaining_stdout:
                print(remaining_stdout, end='', flush=True)
                stdout_lines.append(remaining_stdout)
            if remaining_stderr:
                print(remaining_stderr, end='', file=sys.stderr, flush=True)
                stderr_lines.append(remaining_stderr)
            
            return CommandResult(
                command=command,
                output=''.join(stdout_lines),
                error=''.join(stderr_lines),
                return_code=proc.returncode,
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