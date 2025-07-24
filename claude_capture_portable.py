#!/usr/bin/env python3
"""
Portable Claude capture script that combines user prompts with role-based prompts
from the prompt library and runs Claude Code instances for each combination.

This version is designed to run from any location without requiring installation.
"""

import sys
import json
import xml.etree.ElementTree as ET
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path
import os

# Add the script directory to Python path to ensure local imports work
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Import the embedded logger module
from logger_embedded import DualTagLogger, LogLevel, FileLogHandler, LogFilter, LogEntry

# Try to import pyautogui for keyboard simulation
try:
    import pyautogui
except ImportError:
    pyautogui = None
    print("Warning: pyautogui not installed. Timeout handling will not work.")
    print("Install with: pip install pyautogui")


class ConfiguredLogger:
    """Logger configured based on logging.json"""

    def __init__(self, logging_config_path=None):
        # Use relative path from script directory
        if logging_config_path is None:
            logging_config_path = SCRIPT_DIR / "logging.json"
        self.logging_config = self._load_logging_config(logging_config_path)
        self.logger = DualTagLogger("ClaudeCaptureLogger")
        self._setup_logger()

    def _load_logging_config(self, path):
        """Load logging configuration from JSON file"""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load logging config: {e}")
            # Return default config if file not found
            return {
                "enabled": True,
                "logLevel": "INFO",
                "features": {},
                "modules": {},
                "output": {
                    "format": "json",
                    "destination": "./logs",
                    "rotation": {"enabled": False},
                },
            }

    def _setup_logger(self):
        """Setup logger based on configuration"""
        if not self.logging_config.get("enabled", True):
            return

        # Set log level
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "CRITICAL": LogLevel.CRITICAL,
        }
        self.logger.set_min_level(
            level_map.get(self.logging_config.get("logLevel", "INFO"), LogLevel.INFO)
        )

        # Setup file handler - use relative path
        output_config = self.logging_config.get("output", {})
        log_dir = Path(output_config.get("destination", "./logs"))
        if not log_dir.is_absolute():
            log_dir = SCRIPT_DIR / log_dir
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"claude_capture_{timestamp}.log"

        # Create custom handler that checks tags
        class FilteredFileHandler(FileLogHandler):
            def __init__(self, filepath, format_func, logging_config):
                super().__init__(filepath, format_func)
                self.features = logging_config.get("features", {})
                self.modules = logging_config.get("modules", {})

            def handle(self, entry: LogEntry) -> None:
                # Check if either feature or module tag is enabled
                feature_enabled = self.features.get(entry.feature_tag, False)
                module_enabled = self.modules.get(entry.module_tag, False)

                if feature_enabled or module_enabled:
                    super().handle(entry)

        # Add filtered file handler
        if output_config.get("format") == "json":
            format_func = lambda e: e.to_json()
        else:
            format_func = lambda e: e.to_formatted_string()

        self.logger.add_handler(
            FilteredFileHandler(str(log_file), format_func, self.logging_config)
        )

    def log(self, level, feature_tag, module_tag, function_name, message, **params):
        """Log with automatic filtering based on config"""
        if not self.logging_config.get("enabled", True):
            return

        self.logger.log(level, feature_tag, module_tag, function_name, message, params)


class ClaudeCaptureRunner:
    def __init__(self, prompt_library_path=None, roles_config_path=None):
        # Clean up Zone.Identifier files first
        self._cleanup_zone_files()

        # Use relative paths from script directory
        self.prompt_library_path = (
            Path(prompt_library_path)
            if prompt_library_path
            else SCRIPT_DIR / "prompt_library.xml"
        )
        self.roles_config_path = (
            Path(roles_config_path)
            if roles_config_path
            else SCRIPT_DIR / "roles_config.json"
        )
        self.prompts = {}
        self.roles_config = {}

        # Try multiple Claude paths
        self.claude_path = self._find_claude_command()
        if not self.claude_path:
            print(
                "Error: Claude command not found. Please ensure Claude CLI is installed."
            )
            sys.exit(1)

        self.timeout = 300  # 5 minutes
        self.logger = ConfiguredLogger()

    def _cleanup_zone_files(self):
        """Remove Windows Zone.Identifier files silently"""
        try:
            # Use os.walk instead of rglob to avoid Windows path issues with colons
            for root, dirs, files in os.walk(SCRIPT_DIR):
                for filename in files:
                    if filename.endswith(":Zone.Identifier"):
                        file_path = Path(root) / filename
                        try:
                            file_path.unlink()
                        except Exception:
                            pass  # Ignore errors
        except Exception:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "CLEANUP",
                "_cleanup_zone_files",
                "Error cleaning up Zone.Identifier files: {e}",
            )
            pass  # Ignore all errors

    def _find_claude_command(self):
        """Find the Claude command in various locations with Windows support"""
        # Platform-specific command finder
        if os.name == "nt":  # Windows
            # Try PowerShell approach since claude works through PowerShell
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "claude --version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return "powershell -Command claude"
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        else:
            # Unix/Linux/macOS
            # First try direct command - works if claude is in PATH
            try:
                result = subprocess.run(
                    ["claude", "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return "claude"
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

            # Try using 'which' command
            try:
                result = subprocess.run(
                    ["which", "claude"], capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass

            # Try common Unix paths
            unix_paths = [
                os.path.expanduser("~/.npm-global/bin/claude"),
                "/usr/local/bin/claude",
                "/usr/bin/claude",
            ]

            for path in unix_paths:
                try:
                    result = subprocess.run(
                        [path, "--version"], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        return path
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue

        return None

    def load_prompt_library(self):
        """Load and parse the XML prompt library."""
        self.logger.log(
            LogLevel.INFO,
            "CONFIGURATION",
            "PARSERS",
            "load_prompt_library",
            "Loading XML prompt library",
            path=str(self.prompt_library_path),
        )
        try:
            tree = ET.parse(self.prompt_library_path)
            root = tree.getroot()

            # Parse role prompts
            roles = root.find("roles")
            role_count = 0
            for role_elem in roles.findall("prompt"):
                role_key = role_elem.get("key")
                self.prompts[role_key] = {}
                role_count += 1

                # Get prompts for each level
                level_count = 0
                for level in ["critical", "standard", "best_practice"]:
                    level_elem = role_elem.find(level)
                    if level_elem is not None:
                        self.prompts[role_key][level] = level_elem.text.strip()
                        level_count += 1

                self.logger.log(
                    LogLevel.DEBUG,
                    "CONFIGURATION",
                    "PARSERS",
                    "load_prompt_library",
                    f"Parsed role: {role_key}",
                    levels_found=level_count,
                )

            self.logger.log(
                LogLevel.INFO,
                "CONFIGURATION",
                "PARSERS",
                "load_prompt_library",
                "Successfully loaded prompt library",
                total_roles=role_count,
            )

        except Exception as e:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "PARSERS",
                "load_prompt_library",
                f"Error loading prompt library: {e}",
                exception_type=type(e).__name__,
            )
            print(f"Error loading prompt library: {e}")
            sys.exit(1)

    def load_roles_config(self):
        """Load the JSON roles configuration."""
        self.logger.log(
            LogLevel.INFO,
            "CONFIGURATION",
            "PARSERS",
            "load_roles_config",
            "Loading roles configuration",
            path=str(self.roles_config_path),
        )
        try:
            with open(self.roles_config_path, "r") as f:
                data = json.load(f)
                self.roles_config = data.get("roles", {})

            enabled_roles = sum(
                1 for role, levels in self.roles_config.items() if any(levels.values())
            )
            self.logger.log(
                LogLevel.INFO,
                "CONFIGURATION",
                "PARSERS",
                "load_roles_config",
                "Successfully loaded roles config",
                total_roles=len(self.roles_config),
                enabled_roles=enabled_roles,
            )

        except Exception as e:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "PARSERS",
                "load_roles_config",
                f"Error loading roles config: {e}",
                exception_type=type(e).__name__,
            )
            print(f"Error loading roles config: {e}")
            sys.exit(1)

    def get_enabled_role_prompts(self):
        """Get all enabled role prompts based on configuration."""
        self.logger.log(
            LogLevel.INFO,
            "CODE_ANALYSIS",
            "ANALYZERS",
            "get_enabled_role_prompts",
            "Processing enabled roles",
        )
        enabled_prompts = []

        for role_name, levels in self.roles_config.items():
            # Check if at least one level is enabled for this role
            if any(levels.values()):
                # Combine prompts from enabled levels
                combined_prompt = []
                enabled_levels = []

                if role_name in self.prompts:
                    for level in ["critical", "standard", "best_practice"]:
                        if (
                            levels.get(level, False)
                            and level in self.prompts[role_name]
                        ):
                            combined_prompt.append(self.prompts[role_name][level])
                            enabled_levels.append(level)

                    if combined_prompt:
                        enabled_prompts.append(
                            {"role": role_name, "prompt": "\n\n".join(combined_prompt)}
                        )
                        self.logger.log(
                            LogLevel.DEBUG,
                            "CODE_ANALYSIS",
                            "ANALYZERS",
                            "get_enabled_role_prompts",
                            f"Enabled role: {role_name}",
                            enabled_levels=enabled_levels,
                            prompt_length=len("\n\n".join(combined_prompt)),
                        )

        self.logger.log(
            LogLevel.INFO,
            "CODE_ANALYSIS",
            "ANALYZERS",
            "get_enabled_role_prompts",
            f"Found {len(enabled_prompts)} enabled role(s)",
        )
        return enabled_prompts

    def handle_timeout(self, process):
        """Handle timeout by simulating keyboard input."""
        self.logger.log(
            LogLevel.WARNING,
            "MONITORING",
            "HANDLERS",
            "handle_timeout",
            "Timeout reached for Claude process",
            process_pid=process.pid,
        )
        if pyautogui:
            try:
                self.logger.log(
                    LogLevel.INFO,
                    "MONITORING",
                    "HANDLERS",
                    "handle_timeout",
                    "Simulating keyboard input",
                )
                pyautogui.press("enter")
                time.sleep(2)
                pyautogui.write("1")
                pyautogui.press("enter")
                self.logger.log(
                    LogLevel.INFO,
                    "MONITORING",
                    "HANDLERS",
                    "handle_timeout",
                    "Keyboard simulation completed",
                )
            except Exception as e:
                self.logger.log(
                    LogLevel.ERROR,
                    "ERROR_HANDLING",
                    "HANDLERS",
                    "handle_timeout",
                    f"Error during keyboard simulation: {e}",
                    exception_type=type(e).__name__,
                )
        else:
            self.logger.log(
                LogLevel.WARNING,
                "MONITORING",
                "HANDLERS",
                "handle_timeout",
                "pyautogui not available for timeout handling",
            )
            print("\nTimeout reached but pyautogui not available.")

    def run_claude_with_prompt(self, combined_prompt, role_name):
        """Run Claude Code with the combined prompt and capture output."""
        print(f"\n{'='*60}")
        print(f"Running Claude Code for role: {role_name}")
        print(f"{'='*60}")

        self.logger.log(
            LogLevel.INFO,
            "CODE_GENERATION",
            "SERVICES",
            "run_claude_with_prompt",
            f"Starting Claude Code for role: {role_name}",
            prompt_length=len(combined_prompt),
        )

        # Build command based on platform
        if self.claude_path.startswith("powershell -Command"):
            # Windows PowerShell approach
            cmd = [
                "powershell",
                "-Command",
                f"claude --print '{combined_prompt.replace(chr(39), chr(34))}'",
            ]
            print(
                f"[DEBUG] Using PowerShell command, prompt length: {len(combined_prompt)}"
            )
        else:
            # Direct approach for Unix/Linux/macOS
            cmd = [self.claude_path, "--print", combined_prompt]
            print(f"[DEBUG] Using direct command: {self.claude_path}")

        self.logger.log(
            LogLevel.DEBUG,
            "CODE_GENERATION",
            "SERVICES",
            "run_claude_with_prompt",
            "Executing Claude command",
            command=" ".join(cmd[:2] + ["<prompt>"]),
        )

        print("[DEBUG] About to start subprocess...")

        try:
            # Set up timeout handling
            start_time = time.time()
            print("[DEBUG] Creating subprocess with Popen...")
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print(f"[DEBUG] Subprocess started with PID: {process.pid}")

            self.logger.log(
                LogLevel.DEBUG,
                "MONITORING",
                "SERVICES",
                "run_claude_with_prompt",
                "Claude process started",
                pid=process.pid,
            )

            # Create a timer for timeout handling
            timer = threading.Timer(self.timeout, self.handle_timeout, [process])
            timer.start()
            print(
                f"[DEBUG] Waiting for process to complete (timeout: {self.timeout}s)..."
            )

            # Wait for process to complete
            stdout, stderr = process.communicate()
            timer.cancel()
            print(f"[DEBUG] Process completed!")

            elapsed_time = time.time() - start_time

            self.logger.log(
                LogLevel.INFO,
                "CODE_GENERATION",
                "SERVICES",
                "run_claude_with_prompt",
                f"Claude process completed for role: {role_name}",
                return_code=process.returncode,
                elapsed_time=f"{elapsed_time:.2f}s",
                stdout_length=len(stdout),
                stderr_length=len(stderr),
            )

            if process.returncode != 0:
                self.logger.log(
                    LogLevel.ERROR,
                    "ERROR_HANDLING",
                    "SERVICES",
                    "run_claude_with_prompt",
                    f"Claude returned non-zero code for role: {role_name}",
                    return_code=process.returncode,
                    stderr=stderr[:500],
                )  # Log first 500 chars of error

            return {
                "role": role_name,
                "prompt": combined_prompt,
                "response": stdout,
                "error": stderr,
                "return_code": process.returncode,
                "timestamp": datetime.now().isoformat(),
                "elapsed_time": elapsed_time,
            }

        except Exception as e:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "SERVICES",
                "run_claude_with_prompt",
                f"Exception during Claude execution: {e}",
                exception_type=type(e).__name__,
                role=role_name,
            )
            return {
                "role": role_name,
                "prompt": combined_prompt,
                "response": "",
                "error": str(e),
                "return_code": -1,
                "timestamp": datetime.now().isoformat(),
                "elapsed_time": time.time() - start_time,
            }

    def init_log_file(self, user_prompt):
        """Initialize the log file and return its name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"claude_capture_log_{timestamp}.txt"

        self.logger.log(
            LogLevel.INFO,
            "FILE_OPERATIONS",
            "SERVICES",
            "init_log_file",
            "Initializing capture log",
            filename=log_filename,
        )

        try:
            with open(log_filename, "w") as f:
                f.write(f"Claude Capture Log\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"User Prompt: {user_prompt}\n")
                f.write(f"{'='*80}\n\n")

            self.logger.log(
                LogLevel.INFO,
                "FILE_OPERATIONS",
                "SERVICES",
                "init_log_file",
                "Successfully initialized capture log",
                filename=log_filename,
            )
            return log_filename

        except Exception as e:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "SERVICES",
                "init_log_file",
                f"Error initializing log file: {e}",
                exception_type=type(e).__name__,
                filename=log_filename,
            )
            print(f"Error initializing log: {e}")
            return None

    def append_result_to_log(self, result, log_filename):
        """Append a single result to the log file immediately."""
        if not log_filename:
            return

        self.logger.log(
            LogLevel.INFO,
            "FILE_OPERATIONS",
            "SERVICES",
            "append_result_to_log",
            "Appending result to log",
            filename=log_filename,
            role=result["role"],
        )

        try:
            with open(log_filename, "a") as f:
                f.write(f"Role: {result['role']}\n")
                f.write(f"Timestamp: {result['timestamp']}\n")
                f.write(f"Return Code: {result['return_code']}\n")
                f.write(f"Elapsed Time: {result.get('elapsed_time', 'N/A')}s\n")
                f.write(f"\nCombined Prompt:\n{'-'*40}\n")
                f.write(f"{result['prompt']}\n")
                f.write(f"\nResponse:\n{'-'*40}\n")
                f.write(f"{result['response']}\n")

                if result["error"]:
                    f.write(f"\nError:\n{'-'*40}\n")
                    f.write(f"{result['error']}\n")

                f.write(f"\n{'='*80}\n\n")
                f.flush()  # Ensure it's written immediately

            self.logger.log(
                LogLevel.INFO,
                "FILE_OPERATIONS",
                "SERVICES",
                "append_result_to_log",
                "Successfully appended result to log",
                filename=log_filename,
            )

        except Exception as e:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "SERVICES",
                "append_result_to_log",
                f"Error appending to log file: {e}",
                exception_type=type(e).__name__,
                filename=log_filename,
            )
            print(f"Error appending to log: {e}")

    def finalize_log(self, results, log_filename):
        """Add summary to the log file."""
        if not log_filename:
            return log_filename

        try:
            successful = sum(1 for r in results if r["return_code"] == 0)
            failed = sum(1 for r in results if r["return_code"] != 0)

            with open(log_filename, "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"SUMMARY\n")
                f.write(f"{'='*80}\n")
                f.write(f"Total roles processed: {len(results)}\n")
                f.write(f"Successful: {successful}\n")
                f.write(f"Failed: {failed}\n")
                f.write(f"Completed: {datetime.now().isoformat()}\n")

            self.logger.log(
                LogLevel.INFO,
                "FILE_OPERATIONS",
                "SERVICES",
                "finalize_log",
                "Successfully finalized capture log",
                filename=log_filename,
                file_size=os.path.getsize(log_filename),
            )
            return log_filename

        except Exception as e:
            self.logger.log(
                LogLevel.ERROR,
                "ERROR_HANDLING",
                "SERVICES",
                "finalize_log",
                f"Error finalizing log file: {e}",
                exception_type=type(e).__name__,
                filename=log_filename,
            )
            print(f"Error finalizing log: {e}")
            return log_filename

    def run(self, user_prompt):
        """Main execution method."""
        self.logger.log(
            LogLevel.INFO,
            "PROJECT_MANAGEMENT",
            "CONTROLLERS",
            "run",
            "Starting Claude capture run",
            user_prompt_length=len(user_prompt),
        )

        # Load configurations
        print("Loading prompt library and configuration...")
        self.load_prompt_library()
        self.load_roles_config()

        # Get enabled role prompts
        enabled_prompts = self.get_enabled_role_prompts()

        if not enabled_prompts:
            self.logger.log(
                LogLevel.WARNING,
                "CONFIGURATION",
                "CONTROLLERS",
                "run",
                "No roles are enabled in configuration",
            )
            print("No roles are enabled in the configuration.")
            return

        # Initialize log file and display filename
        log_file = self.init_log_file(user_prompt)
        if log_file:
            print(f"\n[LOG] Results will be saved to: {log_file}")

        print(f"\nFound {len(enabled_prompts)} enabled role(s)")

        # Run Claude for each enabled role
        results = []
        total_start_time = time.time()

        for idx, role_info in enumerate(enabled_prompts, 1):
            self.logger.log(
                LogLevel.INFO,
                "PROJECT_MANAGEMENT",
                "CONTROLLERS",
                "run",
                f"Processing role {idx}/{len(enabled_prompts)}: {role_info['role']}",
            )

            # Combine user prompt with role prompts
            combined_prompt = f"{user_prompt}\n\n{role_info['prompt']}"

            # Run Claude and capture result
            result = self.run_claude_with_prompt(combined_prompt, role_info["role"])
            results.append(result)

            # Immediately save this result to file
            self.append_result_to_log(result, log_file)

            # Display result
            if result["return_code"] == 0:
                print(
                    f"\n[SUCCESS] Response received and saved for {role_info['role']}"
                )
            else:
                print(
                    f"\n[ERROR] Error occurred for {role_info['role']}: {result['error']}"
                )

        total_elapsed = time.time() - total_start_time

        # Finalize log file with summary
        log_file = self.finalize_log(results, log_file)

        # Display summary
        successful = sum(1 for r in results if r["return_code"] == 0)
        failed = sum(1 for r in results if r["return_code"] != 0)

        self.logger.log(
            LogLevel.INFO,
            "PROJECT_MANAGEMENT",
            "CONTROLLERS",
            "run",
            "Claude capture run completed",
            total_roles=len(results),
            successful=successful,
            failed=failed,
            total_elapsed_time=f"{total_elapsed:.2f}s",
            log_file=log_file,
        )

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"{'='*60}")
        print(f"Total roles processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total time: {total_elapsed:.2f}s")
        print(f"Log file: {log_file}")

        # Final cleanup of Zone.Identifier files
        self._cleanup_zone_files()

        return results


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python claude_capture_portable.py <prompt>")
        print("\nExample:")
        print(
            '  python claude_capture_portable.py "Implement a new authentication system"'
        )
        sys.exit(1)

    user_prompt = sys.argv[1]

    # Create and run the capture runner
    runner = ClaudeCaptureRunner()
    runner.run(user_prompt)


if __name__ == "__main__":
    main()
