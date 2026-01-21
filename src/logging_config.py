"""
Centralized logging configuration for Patient Digital Twin.

Features:
- Configurable via LOG_LEVEL environment variable
- Console output for development with colors
- File output with rotation for debugging/production
- Privacy-conscious: filters PII, only logs UUIDs
"""

import logging
import logging.handlers
import os
import re
import sys
from pathlib import Path
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    # Reset
    RESET = "\033[0m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


class LLMColors:
    """Semantic colors for LLM interaction logging."""

    # Message type colors
    SYSTEM_PROMPT = Colors.BRIGHT_MAGENTA  # System prompts
    HUMAN_INPUT = Colors.BRIGHT_CYAN       # Human/user messages
    AI_RESPONSE = Colors.BRIGHT_GREEN      # AI responses
    TOOL_CALL = Colors.BRIGHT_YELLOW       # Tool invocations
    TOOL_RESULT = Colors.YELLOW            # Tool results
    RAG_CONTEXT = Colors.BLUE              # RAG context

    # Labels with styling
    @staticmethod
    def label(text: str, color: str) -> str:
        """Create a colored label."""
        return f"{color}{Colors.BOLD}[{text}]{Colors.RESET}"

    @staticmethod
    def system(text: str) -> str:
        """Format system prompt text."""
        return f"{LLMColors.SYSTEM_PROMPT}{text}{Colors.RESET}"

    @staticmethod
    def human(text: str) -> str:
        """Format human input text."""
        return f"{LLMColors.HUMAN_INPUT}{text}{Colors.RESET}"

    @staticmethod
    def ai(text: str) -> str:
        """Format AI response text."""
        return f"{LLMColors.AI_RESPONSE}{text}{Colors.RESET}"

    @staticmethod
    def tool(text: str) -> str:
        """Format tool call text."""
        return f"{LLMColors.TOOL_CALL}{text}{Colors.RESET}"

    @staticmethod
    def tool_result(text: str) -> str:
        """Format tool result text."""
        return f"{LLMColors.TOOL_RESULT}{text}{Colors.RESET}"

    @staticmethod
    def rag(text: str) -> str:
        """Format RAG context text."""
        return f"{LLMColors.RAG_CONTEXT}{text}{Colors.RESET}"

    @staticmethod
    def header(msg_type: str) -> str:
        """Create a formatted header for message type."""
        colors = {
            "System": LLMColors.SYSTEM_PROMPT,
            "Human": LLMColors.HUMAN_INPUT,
            "AI": LLMColors.AI_RESPONSE,
            "Tool": LLMColors.TOOL_CALL,
            "ToolResult": LLMColors.TOOL_RESULT,
        }
        color = colors.get(msg_type, Colors.WHITE)
        return f"{color}{Colors.BOLD}━━━ {msg_type.upper()} ━━━{Colors.RESET}"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log output based on level."""

    # Level-specific styling
    LEVEL_STYLES = {
        logging.DEBUG: (Colors.CYAN, "DEBUG"),
        logging.INFO: (Colors.GREEN, "INFO"),
        logging.WARNING: (Colors.YELLOW, "WARN"),
        logging.ERROR: (Colors.RED, "ERROR"),
        logging.CRITICAL: (Colors.BOLD + Colors.BG_RED + Colors.WHITE, "CRIT"),
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """Check if the terminal supports colors."""
        # Disable colors if NO_COLOR env var is set
        if os.environ.get("NO_COLOR"):
            return False
        # Check if stdout is a TTY
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return False
        return True

    def format(self, record: logging.LogRecord) -> str:
        # Get level styling
        color, level_label = self.LEVEL_STYLES.get(
            record.levelno, (Colors.WHITE, record.levelname[:5])
        )

        # Format timestamp with milliseconds
        timestamp = self.formatTime(record, "%H:%M:%S")
        timestamp = f"{timestamp}.{int(record.msecs):03d}"

        # Format logger name (shorten if needed)
        name = record.name
        if name.startswith("patient_twin."):
            name = name[13:]  # Remove prefix for cleaner output

        # Format source location (file:function:line)
        filename = record.filename.replace(".py", "")
        location = f"{filename}:{record.funcName}:{record.lineno}"

        # Format message
        message = record.getMessage()

        if self.use_colors:
            # Colored output with detailed info
            # Line 1: timestamp | level | logger name
            # Line 2: location arrow message
            header = (
                f"{Colors.DIM}{timestamp}{Colors.RESET} "
                f"{Colors.DIM}│{Colors.RESET} "
                f"{color}{Colors.BOLD}{level_label:5}{Colors.RESET} "
                f"{Colors.DIM}│{Colors.RESET} "
                f"{Colors.BRIGHT_BLUE}{name}{Colors.RESET}"
            )
            detail = (
                f"  {Colors.DIM}└─ {Colors.RESET}"
                f"{Colors.MAGENTA}{location}{Colors.RESET}"
                f"{Colors.DIM} → {Colors.RESET}"
                f"{Colors.BRIGHT_WHITE}{message}{Colors.RESET}"
            )
            formatted = f"{header}\n{detail}"

            # Add exception info if present
            if record.exc_info:
                exc_text = self.formatException(record.exc_info)
                # Indent and color exception
                exc_lines = exc_text.split("\n")
                exc_formatted = "\n".join(
                    f"  {Colors.DIM}│{Colors.RESET} {Colors.RED}{line}{Colors.RESET}"
                    for line in exc_lines
                )
                formatted += f"\n{exc_formatted}"
        else:
            # Plain output (no colors)
            formatted = f"{timestamp} | {level_label:5} | {name} | {location} | {message}"
            if record.exc_info:
                formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class PIIFilter(logging.Filter):
    """Filter that redacts potential PII from log messages."""

    PATTERNS = [
        # Names
        (r"\b(first_name|last_name|name)\s*[:=]\s*[\"']?[\w\s]+[\"']?", r"\1=[REDACTED]"),
        # Date of birth
        (r"\b(dob|date_of_birth|birth_date)\s*[:=]\s*[\d\-/]+", r"\1=[REDACTED]"),
        # Phone numbers
        (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        # Email addresses
        (r"\b[\w.-]+@[\w.-]+\.\w+\b", "[EMAIL_REDACTED]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact PII from log messages."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        return True


# Module-level state
_logging_initialized = False
_root_logger: Optional[logging.Logger] = None


def setup_logging(
    log_to_file: bool = True,
    log_dir: str = "logs",
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        log_to_file: Whether to write logs to file
        log_dir: Directory for log files

    Returns:
        Root logger configured for the application
    """
    global _logging_initialized, _root_logger

    if _logging_initialized and _root_logger:
        return _root_logger

    # Get log level from environment or default to INFO
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create logs directory
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

    # Root logger for application
    logger = logging.getLogger("patient_twin")
    logger.setLevel(log_level)
    logger.handlers.clear()

    # Add PII filter
    pii_filter = PIIFilter()

    # Console handler (always enabled, with colors)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredFormatter(use_colors=True))
    console_handler.addFilter(pii_filter)
    logger.addHandler(console_handler)

    # File handler (optional, with rotation)
    if log_to_file:
        file_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
        )

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(file_format))
        file_handler.addFilter(pii_filter)
        logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _logging_initialized = True
    _root_logger = logger

    logger.info(f"Logging initialized: level={log_level_name}, file={log_to_file}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.

    Args:
        name: Module name (e.g., "agents.medical_assistant")

    Returns:
        Logger instance for the module
    """
    # Ensure logging is set up
    if not _logging_initialized:
        setup_logging()

    return logging.getLogger(f"patient_twin.{name}")
