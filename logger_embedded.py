#!/usr/bin/env python3
"""
Embedded Logger Module - Part of the portable claude_capture package
This is a simplified version of the logger module with no external dependencies.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import os
import threading
from pathlib import Path


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """
    Represents a single log entry with all required metadata
    """
    timestamp: float
    formatted_timestamp: str
    level: LogLevel
    feature_tag: str
    module_tag: str
    function_name: str
    message: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    thread_id: int = field(default_factory=lambda: threading.get_ident())
    process_id: int = field(default_factory=os.getpid)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary format"""
        return {
            "timestamp": self.timestamp,
            "formatted_timestamp": self.formatted_timestamp,
            "level": self.level.value,
            "feature_tag": self.feature_tag,
            "module_tag": self.module_tag,
            "function_name": self.function_name,
            "message": self.message,
            "parameters": self.parameters,
            "thread_id": self.thread_id,
            "process_id": self.process_id
        }
    
    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_formatted_string(self) -> str:
        """Convert to human-readable log format"""
        params_str = json.dumps(self.parameters) if self.parameters else "{}"
        return (
            f"[{self.formatted_timestamp}] [{self.level.value}] "
            f"[Feature: {self.feature_tag}] [Module: {self.module_tag}] "
            f"[{self.function_name}] {self.message} | Params: {params_str}"
        )


class LogFilter:
    """Filter logs based on various criteria"""
    
    def __init__(self,
                 feature_tags: Optional[List[str]] = None,
                 module_tags: Optional[List[str]] = None,
                 levels: Optional[List[LogLevel]] = None,
                 start_time: Optional[float] = None,
                 end_time: Optional[float] = None,
                 function_names: Optional[List[str]] = None):
        self.feature_tags = set(feature_tags) if feature_tags else None
        self.module_tags = set(module_tags) if module_tags else None
        self.levels = set(levels) if levels else None
        self.start_time = start_time
        self.end_time = end_time
        self.function_names = set(function_names) if function_names else None
    
    def matches(self, entry: LogEntry) -> bool:
        """Check if a log entry matches the filter criteria"""
        if self.feature_tags and entry.feature_tag not in self.feature_tags:
            return False
        if self.module_tags and entry.module_tag not in self.module_tags:
            return False
        if self.levels and entry.level not in self.levels:
            return False
        if self.start_time and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp > self.end_time:
            return False
        if self.function_names and entry.function_name not in self.function_names:
            return False
        return True


class LogStorage:
    """Handles storage and retrieval of log entries"""
    
    def __init__(self, max_memory_entries: int = 10000):
        self._entries: List[LogEntry] = []
        self._lock = threading.Lock()
        self.max_memory_entries = max_memory_entries
        
        # Indexes for fast lookup
        self._feature_index: Dict[str, List[LogEntry]] = defaultdict(list)
        self._module_index: Dict[str, List[LogEntry]] = defaultdict(list)
    
    def add(self, entry: LogEntry) -> None:
        """Add a new log entry"""
        with self._lock:
            self._entries.append(entry)
            self._feature_index[entry.feature_tag].append(entry)
            self._module_index[entry.module_tag].append(entry)
            
            # Manage memory by removing old entries if needed
            if len(self._entries) > self.max_memory_entries:
                oldest = self._entries.pop(0)
                self._feature_index[oldest.feature_tag].remove(oldest)
                self._module_index[oldest.module_tag].remove(oldest)
    
    def get_all(self) -> List[LogEntry]:
        """Get all log entries"""
        with self._lock:
            return self._entries.copy()
    
    def get_by_feature(self, feature_tag: str) -> List[LogEntry]:
        """Get all logs for a specific feature"""
        with self._lock:
            return self._feature_index[feature_tag].copy()
    
    def get_by_module(self, module_tag: str) -> List[LogEntry]:
        """Get all logs for a specific module"""
        with self._lock:
            return self._module_index[module_tag].copy()
    
    def filter(self, log_filter: LogFilter) -> List[LogEntry]:
        """Get filtered log entries"""
        with self._lock:
            return [entry for entry in self._entries if log_filter.matches(entry)]
    
    def clear(self) -> None:
        """Clear all log entries"""
        with self._lock:
            self._entries.clear()
            self._feature_index.clear()
            self._module_index.clear()


class LogHandler:
    """Base class for log handlers"""
    
    def handle(self, entry: LogEntry) -> None:
        """Handle a log entry"""
        raise NotImplementedError


class ConsoleLogHandler(LogHandler):
    """Outputs logs to console"""
    
    def __init__(self, format_func: Optional[Callable[[LogEntry], str]] = None):
        self.format_func = format_func or (lambda e: e.to_formatted_string())
    
    def handle(self, entry: LogEntry) -> None:
        """Print log entry to console"""
        print(self.format_func(entry))


class FileLogHandler(LogHandler):
    """Outputs logs to file"""
    
    def __init__(self, 
                 filepath: str,
                 format_func: Optional[Callable[[LogEntry], str]] = None,
                 rotate_size: Optional[int] = None):
        self.filepath = Path(filepath)
        self.format_func = format_func or (lambda e: e.to_json())
        self.rotate_size = rotate_size
        self._lock = threading.Lock()
    
    def handle(self, entry: LogEntry) -> None:
        """Write log entry to file"""
        with self._lock:
            # Check if rotation is needed
            if self.rotate_size and self.filepath.exists():
                if self.filepath.stat().st_size > self.rotate_size:
                    self._rotate()
            
            # Write the log entry
            with open(self.filepath, 'a') as f:
                f.write(self.format_func(entry) + '\n')
    
    def _rotate(self) -> None:
        """Rotate log file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_name = f"{self.filepath.stem}_{timestamp}{self.filepath.suffix}"
        self.filepath.rename(self.filepath.parent / new_name)


class DualTagLogger:
    """
    Main logger class with dual-tag functionality
    
    This logger allows tagging each log entry with both a user-facing feature tag
    and an internal module tag, enabling analysis from multiple perspectives.
    """
    
    def __init__(self, name: str = "AppLogger"):
        self.name = name
        self.storage = LogStorage()
        self.handlers: List[LogHandler] = []
        self._min_level = LogLevel.DEBUG
    
    def add_handler(self, handler: LogHandler) -> None:
        """Add a log handler"""
        self.handlers.append(handler)
    
    def set_min_level(self, level: LogLevel) -> None:
        """Set minimum log level"""
        self._min_level = level
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if we should log at this level"""
        level_values = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        return level_values[level] >= level_values[self._min_level]
    
    def log(self,
            level: LogLevel,
            feature_tag: str,
            module_tag: str,
            function_name: str,
            message: str,
            parameters: Optional[Dict[str, Any]] = None) -> None:
        """
        Create a log entry with all required information
        
        Args:
            level: Log severity level
            feature_tag: User-facing feature this log relates to
            module_tag: Internal module this log belongs to
            function_name: Name of the function generating the log
            message: Log message
            parameters: Dictionary of parameters and their values
        """
        if not self._should_log(level):
            return
        
        timestamp = time.time()
        formatted_timestamp = datetime.fromtimestamp(timestamp).isoformat()
        
        entry = LogEntry(
            timestamp=timestamp,
            formatted_timestamp=formatted_timestamp,
            level=level,
            feature_tag=feature_tag,
            module_tag=module_tag,
            function_name=function_name,
            message=message,
            parameters=parameters or {}
        )
        
        # Store the entry
        self.storage.add(entry)
        
        # Send to handlers
        for handler in self.handlers:
            try:
                handler.handle(entry)
            except Exception as e:
                # Log handler errors shouldn't crash the application
                print(f"Error in log handler: {e}")
    
    def debug(self, feature_tag: str, module_tag: str, function_name: str,
              message: str, **params) -> None:
        """Log debug message"""
        self.log(LogLevel.DEBUG, feature_tag, module_tag, function_name, message, params)
    
    def info(self, feature_tag: str, module_tag: str, function_name: str,
             message: str, **params) -> None:
        """Log info message"""
        self.log(LogLevel.INFO, feature_tag, module_tag, function_name, message, params)
    
    def warning(self, feature_tag: str, module_tag: str, function_name: str,
                message: str, **params) -> None:
        """Log warning message"""
        self.log(LogLevel.WARNING, feature_tag, module_tag, function_name, message, params)
    
    def error(self, feature_tag: str, module_tag: str, function_name: str,
              message: str, **params) -> None:
        """Log error message"""
        self.log(LogLevel.ERROR, feature_tag, module_tag, function_name, message, params)
    
    def critical(self, feature_tag: str, module_tag: str, function_name: str,
                 message: str, **params) -> None:
        """Log critical message"""
        self.log(LogLevel.CRITICAL, feature_tag, module_tag, function_name, message, params)
    
    def get_logs_by_feature(self, feature_tag: str) -> List[LogEntry]:
        """Get all logs for a specific feature"""
        return self.storage.get_by_feature(feature_tag)
    
    def get_logs_by_module(self, module_tag: str) -> List[LogEntry]:
        """Get all logs for a specific module"""
        return self.storage.get_by_module(module_tag)
    
    def get_filtered_logs(self, log_filter: LogFilter) -> List[LogEntry]:
        """Get filtered logs"""
        return self.storage.filter(log_filter)
    
    def get_all_logs(self) -> List[LogEntry]:
        """Get all logs"""
        return self.storage.get_all()
    
    def export_logs(self, 
                    filepath: str,
                    log_filter: Optional[LogFilter] = None,
                    format_type: str = "json") -> None:
        """
        Export logs to file
        
        Args:
            filepath: Path to export file
            log_filter: Optional filter to apply
            format_type: Export format ('json', 'csv', 'text')
        """
        logs = self.storage.filter(log_filter) if log_filter else self.storage.get_all()
        
        with open(filepath, 'w') as f:
            if format_type == "json":
                log_dicts = [log.to_dict() for log in logs]
                json.dump(log_dicts, f, indent=2)
            elif format_type == "csv":
                # Simple CSV implementation without external dependencies
                if logs:
                    fieldnames = logs[0].to_dict().keys()
                    # Write header
                    f.write(','.join(fieldnames) + '\n')
                    # Write rows
                    for log in logs:
                        log_dict = log.to_dict()
                        values = [str(log_dict[field]).replace(',', ';') for field in fieldnames]
                        f.write(','.join(values) + '\n')
            else:  # text
                for log in logs:
                    f.write(log.to_formatted_string() + '\n')