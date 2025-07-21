# Claude Capture Portable - Usage Guide

## Quick Setup

1. **Copy the `claude_capture_portable` folder** to any location
2. **Run from anywhere:**
   ```bash
   python3 /path/to/claude_capture_portable/run_claude_capture.py "Your prompt"
   ```

## Creating Project Launchers

To use from any project directory:

```bash
# In your project directory
python3 /path/to/claude_capture_portable/run_claude_capture.py --create-launcher

# Now you can use
python3 claude_capture.py "Your prompt here"
```

## Configuration

### Enable/Disable Analysis Types

Edit `roles_config.json`:
```json
{
  "roles": {
    "error handling": {
      "critical": true,    // Enable critical error analysis
      "standard": true,    // Enable standard error analysis  
      "best_practice": false  // Disable best practice suggestions
    },
    "security review": {
      "critical": false,   // Disable security analysis
      "standard": false,
      "best_practice": false
    }
  }
}
```

### Logging Control

Edit `logging.json`:
```json
{
  "enabled": true,
  "logLevel": "INFO",
  "features": {
    "CODE_GENERATION": true,   // Log code generation steps
    "ERROR_HANDLING": true,    // Log error handling
    "MONITORING": true         // Log execution monitoring
  }
}
```

## Example Usage

```bash
# Basic code analysis
python3 claude_capture.py "Review this authentication function for security issues"

# Architecture design
python3 claude_capture.py "Design a REST API for user management"

# Code review
python3 claude_capture.py "Analyze this database schema for performance bottlenecks"

# Skip dependency setup (faster for repeated runs)
python3 run_claude_capture.py --no-setup "Your prompt"
```

### ✨ New Features

**📄 Incremental Saving**: Results are saved after each role completes, so if the process is interrupted, you won't lose any completed analyses.

**🔍 Progress Tracking**: The script shows the log filename at startup:
```
📄 Results will be saved to: claude_capture_log_20250720_183045.txt
```

**✅ Real-time Feedback**: Each completed role shows immediate confirmation:
```
✅ Response received and saved for error handling
✅ Response received and saved for security review
```

**🧹 Auto-cleanup**: Automatically removes Windows Zone.Identifier files before and after running.

## Customizing for Projects

1. **Copy the portable folder** to your project
2. **Edit configurations** for project-specific needs:
   - `roles_config.json` - Which analysis types to run
   - `logging.json` - What to log
   - `prompt_library.xml` - Custom prompts for your domain

3. **Create project-specific prompts** in `prompt_library.xml`

## Troubleshooting

### Windows Zone.Identifier Files
If you see `*.Zone.Identifier` files, run:
```bash
python3 cleanup.py
```

### Claude Not Found
Ensure Claude CLI is installed and in your PATH:
```bash
which claude  # Should show the path to claude
```

### Permission Issues
The script uses `--user` flag for package installation, which doesn't require admin rights.

### pyautogui Installation Fails
This is optional - the script will continue without it. Timeout handling will be limited but everything else works.

## File Structure

```
claude_capture_portable/
├── run_claude_capture.py      # Main bootstrap script
├── claude_capture_portable.py # Core capture logic
├── logger_embedded.py         # Embedded logging (no dependencies)
├── roles_config.json          # Configure which roles to run
├── logging.json               # Configure logging behavior
├── prompt_library.xml         # Role-based prompts
├── cleanup.py                 # Remove Windows artifacts
├── README.md                  # Overview documentation
└── USAGE.md                   # This file
```

## Advanced Features

### Multiple Configurations
Keep different configurations for different projects:
```bash
cp claude_capture_portable my_backend_analysis/
cp claude_capture_portable my_frontend_analysis/
# Edit each copy's config files differently
```

### Custom Prompts
Add your own analysis types in `prompt_library.xml`:
```xml
<prompt key="my_custom_analysis">
    <critical>Check for critical custom issues...</critical>
    <standard>Review standard custom patterns...</standard>
    <best_practice>Suggest custom best practices...</best_practice>
</prompt>
```

Then enable in `roles_config.json`:
```json
{
  "roles": {
    "my_custom_analysis": {
      "critical": true,
      "standard": true,
      "best_practice": false
    }
  }
}
```