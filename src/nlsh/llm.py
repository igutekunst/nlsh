"""LLM interface for generating shell commands"""

import os
import re
from typing import List
import openai
from dotenv import load_dotenv

from .context import ContextInfo


class LLMInterface:
    """Interface for LLM-based command generation"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Default to cost-effective model
        
    def generate_commands(self, prompt: str, context: ContextInfo) -> List[str]:
        """Generate shell commands based on natural language prompt and context"""
        
        # Create context-aware system prompt
        system_prompt = self._create_system_prompt(context)
        
        # Create user prompt with context
        user_prompt = self._create_user_prompt(prompt, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic output
                max_tokens=500,   # Reasonable limit for command generation
            )
            
            # Extract and parse commands from response
            commands = self._parse_commands(response.choices[0].message.content)
            return commands
            
        except Exception as e:
            raise Exception(f"LLM API error: {e}")
    
    def _create_system_prompt(self, context: ContextInfo) -> str:
        """Create system prompt with shell and context information"""
        
        shell_name = context.shell_info.get('name', 'bash')
        shell_features = context.shell_info.get('features', {})
        
        system_prompt = f"""You are an expert command-line assistant that generates {shell_name} shell commands.

Key Guidelines:
1. Generate ONLY valid {shell_name} commands that can be executed directly
2. Respond with one or more commands, each on a separate line
3. Do NOT include explanations, comments, or markdown formatting
4. Do NOT use backticks or code blocks
5. Be precise and safe - avoid destructive operations unless explicitly requested
6. Consider the current working directory and available files when generating commands
7. Use shell-appropriate syntax for {shell_name}

Shell Features Available:
{self._format_shell_features(shell_features)}

Current Context Will Be Provided In User Message.

Example Response Format:
ls -la
cd subdirectory
grep -r "pattern" *.txt

Remember: Output ONLY the commands, nothing else."""

        return system_prompt
    
    def _create_user_prompt(self, prompt: str, context: ContextInfo) -> str:
        """Create user prompt with context and request"""
        from .context import ContextManager
        
        # Format context for LLM
        context_manager = ContextManager()
        formatted_context = context_manager.format_context_for_llm(context, context.shell_info)
        
        user_prompt = f"""{formatted_context}

User Request: {prompt}

Generate the appropriate shell commands to fulfill this request."""

        return user_prompt
    
    def _format_shell_features(self, features: dict) -> str:
        """Format shell features for the system prompt"""
        if not features:
            return "Standard shell features available"
            
        feature_lines = []
        for key, value in features.items():
            if isinstance(value, bool) and value:
                feature_lines.append(f"- {key.replace('_', ' ').title()}: Yes")
            elif isinstance(value, str):
                feature_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            elif isinstance(value, list):
                feature_lines.append(f"- {key.replace('_', ' ').title()}: {', '.join(value)}")
                
        return '\n'.join(feature_lines) if feature_lines else "Standard shell features available"
    
    def _parse_commands(self, response_text: str) -> List[str]:
        """Parse commands from LLM response"""
        if not response_text:
            return []
        
        # Clean up the response
        response_text = response_text.strip()
        
        # Split into lines and clean each command
        lines = response_text.split('\n')
        commands = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Skip obvious non-command lines (explanations, etc.)
            if line.startswith('#') or line.startswith('//'):
                continue
            if line.startswith('Here') or line.startswith('The command'):
                continue
            if '```' in line:
                continue
                
            # Remove any numbering (1. command, - command, etc.)
            if re.match(r'^\d+\.?\s+', line):
                line = re.sub(r'^\d+\.?\s+', '', line)
            elif line.startswith('- '):
                line = line[2:].strip()
            elif line.startswith('* '):
                line = line[2:].strip()
                
            # Basic validation - should look like a command
            if line and not line.isspace():
                commands.append(line)
        
        return commands[:5]  # Limit to 5 commands max for safety
    
    def validate_api_key(self) -> bool:
        """Validate that OpenAI API key is working"""
        try:
            # Make a minimal API call to test the key
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False 