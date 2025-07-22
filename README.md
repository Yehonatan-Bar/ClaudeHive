# Claude Capture Portable

A portable version of the Claude capture tool that can run from any location without requiring installation.

## Quick Start

1. **Copy this directory** to any location on your system
2. **Run from the portable directory:**
   ```bash
   python3 run_claude_capture.py "Your prompt here"
   ```

3. **Or create a launcher** in your current project:
   ```bash
   python3 run_claude_capture.py --create-launcher
   # Then use: python3 claude_capture.py "Your prompt here"
   ```

## Features

- **Zero Installation**: Works with just python3 3.6+ and Claude CLI
- **Portable**: Copy and run from any directory
- **Role-based Analysis**: Runs Claude with multiple specialized prompts
- **Configurable**: Customize roles and logging through JSON files
- **Self-contained**: All dependencies are embedded or automatically installed
- **Incremental Saving**: Results saved after each iteration (no data loss if interrupted)
- **Auto-cleanup**: Automatically removes Windows Zone.Identifier files
- **Progress Tracking**: Shows filename at startup and saves progress in real-time

## Usage Examples

```bash
# Basic usage
python3 run_claude_capture.py "Create a python3 web scraper"

# Code review
python3 run_claude_capture.py "Review this authentication system for security issues"

# Architecture analysis  
python3 run_claude_capture.py "Design a microservices architecture for an e-commerce platform"
```

## Configuration

### `roles_config.json`
Controls which analysis roles are enabled:
```json
{
  "roles": {
    "error handling": {
      "critical": true,
      "standard": true,
      "best_practice": false
    },
    "security review": {
      "critical": false,
      "standard": false,
      "best_practice": false
    }
  }
}
```

### `logging.json`
Controls logging behavior:
```json
{
  "enabled": true,
  "logLevel": "INFO",
  "features": {
    "CODE_GENERATION": true,
    "ERROR_HANDLING": true
  }
}
```

### `prompt_library.xml`
Contains the role-based prompts used for analysis. You can customize these prompts to match your specific needs.

## Requirements

- **python3 3.6+** (built-in modules only)
- **Claude CLI** installed and configured
- **Optional**: `pyautogui` for timeout handling (auto-installed if needed)

## Files

- `run_claude_capture.py` - Main bootstrap script
- `claude_capture_portable.py` - Core capture logic
- `logger_embedded.py` - Embedded logging system
- `roles_config.json` - Role configuration
- `logging.json` - Logging configuration  
- `prompt_library.xml` - Role-based prompts

## How It Works

1. **Bootstrap**: `run_claude_capture.py` checks dependencies and sets up environment
2. **Configuration**: Loads roles and logging settings from JSON files
3. **Prompt Generation**: Combines your prompt with enabled role prompts from XML
4. **Execution**: Runs Claude CLI for each enabled role combination
5. **Output**: Displays results and saves detailed logs

## Customization

To customize for your needs:

1. **Edit `roles_config.json`** to enable/disable analysis types
2. **Modify `prompt_library.xml`** to add custom prompts or change existing ones
3. **Adjust `logging.json`** to control what gets logged
4. **Copy to new projects** - each copy can have different configurations

## Troubleshooting

- **Claude not found**: Ensure Claude CLI is installed and in PATH
- **Permission errors**: The script will try to install optional packages with `--user` flag
- **Import errors**: Make sure you're running from the portable directory or use the launcher

## Advanced Usage

### Creating Project-Specific Launchers

```bash
# In your project directory
/path/to/claude_capture_portable/run_claude_capture.py --create-launcher

# Now you can use
python3 claude_capture.py "Analyze this codebase"
```

### Running Without Setup

```bash
# Skip dependency checking (faster for repeated runs)
python3 run_claude_capture.py --no-setup "Your prompt"
```

### Custom Configuration

Copy the portable directory and modify the JSON/XML files for project-specific needs:

```bash
cp -r claude_capture_portable my_project_claude/
cd my_project_claude/
# Edit roles_config.json, logging.json, prompt_library.xml
python3 run_claude_capture.py "Project-specific prompt"
```