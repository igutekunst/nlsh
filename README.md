# nlsh - Natural Language Shell

An AI-augmented command line shell that wraps your existing shell and adds natural language command generation via LLM.

## Features

- **Shell Compatibility**: Works with any shell (bash, zsh, fish, sh)
- **Natural Language Commands**: Use `llm: <prompt>` to generate shell commands from natural language
- **Rich Context**: LLM has access to current directory, file listings, shell info, and environment
- **Command History**: Full SQLite-based history tracking of all commands and LLM interactions
- **Safety First**: Always prompts for confirmation before executing AI-generated commands
- **Rich Terminal Output**: Beautiful terminal interface powered by Rich
- **Streaming Responses**: Real-time streaming with animated progress spinners for tool calls
- **Tool-Enabled AI**: AI can execute shell commands, read files, and gather system information with confirmation

## Installation

### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- `uv` package manager (recommended) or pip

### Using uv (recommended)

```bash
# Clone the repository
git clone <repository-url>
cd nlsh

# Install with uv
uv pip install -e .

# Or install dependencies directly
uv pip install rich openai typer python-dotenv
```

### Using pip

```bash
pip install -e .
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

3. Optional: Configure the LLM model (default is gpt-4o-mini for cost efficiency):
```bash
OPENAI_MODEL=gpt-4o  # or gpt-3.5-turbo, etc.
```

## Usage

### Starting nlsh

```bash
nlsh
```

This will start the natural language shell interface with streaming enabled by default.

#### Command Line Options

```bash
nlsh --help                    # Show all available options
nlsh --no-stream              # Disable streaming (faster but less interactive)
nlsh --use-simple             # Use simple OpenAI interface instead of LangGraph
nlsh --debug                  # Enable debug mode
```

### Commands

#### Regular Shell Commands
Just type commands normally - they'll be passed through to your default shell:

```bash
bitchin-shell $ ls -la
bitchin-shell $ cd src
bitchin-shell $ git status
```

#### Natural Language Commands
Use the `llm:` prefix for AI-generated commands:

```bash
nlsh $ llm: find all python files larger than 1MB
nlsh $ llm: show me git commits from last week
nlsh $ llm: compress all jpg files in this directory
nlsh $ llm: install the requests package
```

The AI will:
1. **Analyze your request** and current context (working directory, files, shell type)
2. **Use tools** to gather additional information if needed (with animated progress indicators)
3. **Generate appropriate shell commands**
4. **Show you the commands and ask for confirmation**
5. **Execute the commands if you approve**

#### Exiting
```bash
bitchin-shell $ exit
# or
bitchin-shell $ quit
```

## How It Works

### Streaming Interface
nlsh features a modern streaming interface that shows:

- **🔄 Animated spinners** for tool operations (file reading, directory listing, etc.)
- **📁 Real-time tool call descriptions** ("Reading file: config.py", "Checking git status")
- **💬 Streaming AI responses** as they're generated
- **✅ Tool completion confirmations** with result previews

### Tool-Enabled AI
The AI has access to powerful tools:

- **📁 File Operations**: List, read, and find files
- **⚡ Shell Commands**: Execute commands with mandatory confirmation
- **📊 Git Integration**: Check status, view logs, and diffs
- **💻 System Info**: Access environment and system details
- **🌳 Directory Trees**: Navigate and understand project structure

### Context Awareness
The LLM receives rich context about your environment:

- **Current working directory** and file listings
- **Shell information** (type, version, features)
- **System information** (OS, architecture)
- **Environment variables** (PATH, HOME, etc.)
- **Recent command history**

### Shell Detection
nlsh automatically detects your shell from the `$SHELL` environment variable and adapts:

- **bash/zsh**: Standard POSIX syntax
- **fish**: Fish-specific syntax and features
- **sh**: Basic POSIX compatibility mode

### History Tracking
All interactions are stored in SQLite database (`~/.nlsh/history.db`):

- Shell commands and their output
- LLM interactions (prompts, generated commands, execution results)
- Context snapshots
- Session information

## Examples

### File Operations
```bash
nlsh $ llm: find all Python files modified in the last 24 hours
# Generates: find . -name "*.py" -mtime -1

nlsh $ llm: backup all my config files to a tar archive
# Generates: tar -czf config_backup_$(date +%Y%m%d).tar.gz ~/.bashrc ~/.vimrc ~/.gitconfig
```

### Development Tasks
```bash
nlsh $ llm: run the tests and show coverage
# Generates: python -m pytest --cov=. --cov-report=term-missing

nlsh $ llm: start a local web server on port 8080
# Generates: python -m http.server 8080
```

### System Administration
```bash
nlsh $ llm: show me processes using more than 100MB of memory
# Generates: ps aux | awk '$6 > 102400 {print $0}' | sort -k6 -nr

nlsh $ llm: check disk usage and show largest directories
# Generates: du -h --max-depth=1 | sort -hr
```

## Architecture

```
nlsh/
├── src/nlsh/
│   ├── cli.py          # Main CLI interface and REPL loop
│   ├── shell.py        # Shell detection and command execution
│   ├── llm.py          # OpenAI integration and command generation
│   ├── context.py      # Environment and filesystem context gathering
│   └── history.py      # SQLite-based history management
├── pyproject.toml      # Python package configuration
└── README.md
```

## Development

### Running from Source

```bash
# Install in development mode
uv pip install -e .

# Run directly
python -m nlsh.cli

# Or run the installed command
nlsh
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

**"OPENAI_API_KEY environment variable is required"**
- Make sure you've created a `.env` file with your OpenAI API key
- Verify the key is correct and has sufficient credits

**"Shell detection failed"**
- nlsh falls back to `sh` if it can't detect your shell
- You can manually set `SHELL` environment variable if needed

**"Permission denied" errors**
- Make sure nlsh has permission to create the history database in `~/.nlsh/`
- Check file permissions in your working directory

### Debug Mode

Run with debug flag to see detailed error information:

```bash
nlsh --debug
```

## Roadmap

### Phase 2 Features (Planned)
- **Contextual Memory**: LLM remembers previous session context
- **Follow-up Commands**: "rerun that but with sudo", "do the same for .js files"  
- **Trusted Commands**: Auto-execute safe commands without confirmation
- **Plugin System**: Extensible AI tools and integrations
- **Better Shell Integration**: Tab completion, command substitution

### Phase 3 Features (Future)
- **Full Shell Replacement**: Built-in shell features, not just wrapper
- **Advanced Context**: Git repository awareness, project type detection
- **Collaborative Sessions**: Shared session history and context
- **Custom LLM Models**: Support for local/custom models

## License

[License information]

## Credits

Built with:
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Typer](https://github.com/tiangolo/typer) for CLI framework
- [OpenAI](https://openai.com/) for language model integration 