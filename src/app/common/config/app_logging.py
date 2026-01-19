"""
Enhanced logging configuration with color schemes for MCP server.

Color Scheme:
- Entire line: Gray/White (default colorlog colors - preserved exactly)
- Text within [square brackets] in MESSAGE part only: Colored with specified colors
  - BRIGHT_ORANGE: MCP keywords ([MCP], [AUTH], [REQUEST], [TOOLS], [TOOL_CALL], [TOOL_EXEC], [TOOL_RESULT], [RESPONSE])
  - GREEN: Success (SUCCESS, brackets containing "200" or "success", and text containing "status=success" or "| 200 |")
  - RED: Errors (ERROR, CRITICAL, FAILED, FAILURE)
  - MAGENTA: Warnings (WARNING, WARN, FALLBACK, RETRY, TIMEOUT)

IMPORTANT: Only colorizes brackets in the MESSAGE part, not in formatted parts like [%(name)s] or [%(levelname)s]
Also skips ANSI codes like [37m, [0m, [31m, etc.
"""

import logging
import sys
import re
from typing import Optional, Dict

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class EnhancedColoredFormatter(colorlog.ColoredFormatter if COLORLOG_AVAILABLE else logging.Formatter):
    """
    Enhanced colored formatter that colors only text within [square brackets] in the MESSAGE part,
    while keeping the rest of the line in default gray/white colors from colorlog.
    Simplified for MCP server use.
    """
    
    # ANSI color codes - using standard 8-bit colors for IntelliJ/Windows terminal compatibility
    GREEN = '\033[92m'           # Bright green - Success (standard ANSI)
    MAGENTA = '\033[95m'         # Bright magenta - Warnings (standard ANSI)
    BRIGHT_ORANGE = '\033[93m'   # Bright yellow/orange - MCP keywords (standard ANSI, closest to orange)
    RED = '\033[91m'             # Bright red - Errors (standard ANSI)
    RESET = '\033[0m'
    
    # Patterns for text within [square brackets] - RED
    ERROR_BRACKET_PATTERNS = [
        r"\[ERROR\]",
        r"\[CRITICAL\]",
        r"\[EXCEPTION\]",
        r"\[FAILED\]",
        r"\[FAILURE\]",
    ]
    
    # Patterns for text within [square brackets] - MAGENTA (Warnings)
    WARNING_BRACKET_PATTERNS = [
        r"\[WARNING\]",
        r"\[WARN\]",
        r"\[FAILED TO\]",
        r"\[UNABLE TO\]",
        r"\[MISSING\]",
        r"\[NOT FOUND\]",
        r"\[NOT AVAILABLE\]",
        r"\[FALLBACK\]",
        r"\[RETRY\]",
        r"\[TIMEOUT\]",
        r"\[EMPTY\]",
    ]
    
    # Patterns for text within [square brackets] - BRIGHT_ORANGE (MCP keywords)
    MCP_BRACKET_PATTERNS = [
        r"\[MCP\]",
        r"\[MCP_SERVER\]",
        r"\[MCP_PROTOCOL\]",
        r"\[AUTH\]",
        r"\[REQUEST\]",
        r"\[TOOLS\]",
        r"\[TOOL_CALL\]",
        r"\[TOOL_EXEC\]",
        r"\[TOOL_RESULT\]",
        r"\[RESPONSE\]",
    ]
    
    # Patterns for text within [square brackets] - GREEN (Success only)
    SUCCESS_BRACKET_PATTERNS = [
        r"\[TRACE\].*✓",
        r"\[SUCCESS\]",
        r"\[.*SUCCESS.*\]",  # Any bracket containing "SUCCESS"
        r"\[.*200.*\]",       # Any bracket containing "200" (HTTP status code)
        r"\[.*success.*\]",   # Any bracket containing "success" (case-insensitive)
        r"\[.*status.*success.*\]",  # Any bracket containing "status" and "success"
        r"\[.*200.*status.*\]",      # Any bracket containing "200" and "status"
    ]
    
    # Patterns for success keywords in text (not in brackets) - GREEN
    SUCCESS_TEXT_PATTERNS = [
        r'\bstatus\s*=\s*success\b',  # status=success
        r'\|\s*200\s*\|',              # | 200 |
        r'\b200\s+OK\b',                # 200 OK
        r'\bstatus\s*:\s*success\b',   # status: success
    ]
    
    def _colorize_brackets(self, text: str) -> str:
        """
        Colorize ONLY UPPER CASE text within [square brackets] in the MESSAGE part.
        Preserves colorlog's default grey/white formatting for the rest of the line.
        Skips ANSI codes, formatted parts, and lowercase text.
        """
        # IMPORTANT: Protect ANSI escape sequences from being matched as brackets
        # ANSI escape sequences are: \033[ followed by numbers and 'm'
        # We'll temporarily replace them with placeholders before bracket matching
        
        # Pattern to match ANSI escape sequences: \033[ followed by digits, semicolons, and 'm'
        ansi_pattern = r'\033\[[0-9;]*m'
        ansi_placeholders = {}
        placeholder_counter = 0
        
        def replace_ansi_with_placeholder(match):
            nonlocal placeholder_counter
            placeholder = f"__ANSI_PLACEHOLDER_{placeholder_counter}__"
            ansi_placeholders[placeholder] = match.group(0)
            placeholder_counter += 1
            return placeholder
        
        # Replace all ANSI codes with placeholders before bracket matching
        text_protected = re.sub(ansi_pattern, replace_ansi_with_placeholder, text)
        
        # Pattern to match [anything] in the text (now safe from ANSI codes)
        bracket_pattern = r'\[([^\]]+)\]'
        
        def replace_bracket(match):
            bracket_content = match.group(0)  # Full match including brackets: [CONTENT]
            content = match.group(1)  # Content inside brackets: CONTENT
            
            # THUMB RULE: Only colorize UPPER CASE text in brackets
            # Skip if content is not UPPER CASE (preserve grey/white for lowercase)
            if not content.isupper():
                return bracket_content
            
            # Skip ANSI color codes (like [37m, [0m, [31m, [1m, [38;5;77m, etc.)
            # ANSI codes are:
            # - Simple: digits followed by 'm' (like [37m, [0m, [31m)
            # - Complex: digits with semicolons and optional digits/letters ending in 'm' (like [38;5;77m)
            if re.match(r'^\d+[a-z;:]*m$', content) or re.match(r'^\d+[a-z;:]*$', content):
                return bracket_content
            
            # Skip common log levels from format string (INFO, DEBUG, WARNING)
            # ERROR and CRITICAL are NOT skipped - they should be colored red in brackets
            # The log level in the format string is already colored by colorlog (now white),
            # but we DO want to colorize [ERROR] and [CRITICAL] in the message part as red
            if content in ['INFO', 'DEBUG', 'WARNING']:
                return bracket_content
            
            # Determine color based on content (case-insensitive matching)
            # Order matters - check more specific patterns first
            color = None
            
            # Check SUCCESS patterns early (high priority - 200, success keywords)
            # This should be checked before other patterns to ensure success indicators are colored green
            for pattern in self.SUCCESS_BRACKET_PATTERNS:
                if re.search(pattern, bracket_content, re.IGNORECASE):
                    color = self.GREEN
                    break
            
            # Check ERROR patterns
            if not color:
                for pattern in self.ERROR_BRACKET_PATTERNS:
                    if re.search(pattern, bracket_content, re.IGNORECASE):
                        color = self.RED
                        break
            
            # Check WARNING patterns
            if not color:
                for pattern in self.WARNING_BRACKET_PATTERNS:
                    if re.search(pattern, bracket_content, re.IGNORECASE):
                        color = self.MAGENTA
                        break
            
            # Check MCP patterns (MCP keywords - BRIGHT_ORANGE)
            if not color:
                for pattern in self.MCP_BRACKET_PATTERNS:
                    if re.search(pattern, bracket_content, re.IGNORECASE):
                        color = self.BRIGHT_ORANGE
                        break
            
            # If color determined, apply it; otherwise return original
            if color:
                return color + bracket_content + self.RESET
            else:
                return bracket_content
        
        # Replace all [brackets] with colored versions (on protected text)
        result = re.sub(bracket_pattern, replace_bracket, text_protected)
        
        # Restore ANSI escape sequences from placeholders
        for placeholder, ansi_code in ansi_placeholders.items():
            result = result.replace(placeholder, ansi_code)
        
        # THUMB RULE: Do NOT colorize text outside brackets
        # Preserve grey/white combination for all non-bracket text
        # Removed success keyword coloring in text - only UPPER CASE brackets get colored
        # This matches hrb_copilot behavior exactly
        
        # Clean up any double RESET codes that might occur
        # But preserve colorlog's RESET codes - only remove duplicates
        result = re.sub(r'\033\[0m\033\[0m', self.RESET, result)
        
        return result
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with default gray/white colors for the line,
        but color only text within [square brackets] in the MESSAGE part and success keywords.
        """
        # First, let colorlog format the message with default colors (gray/white for INFO)
        if COLORLOG_AVAILABLE:
            formatted = super().format(record)
        else:
            formatted = logging.Formatter.format(self, record)
        
        # Ensure colorlog's default colors are preserved
        # colorlog applies colors via %(log_color)s and %(reset)s in the format string
        # The formatted string should already have ANSI color codes from colorlog
        # We need to preserve these while adding our custom colors to brackets
        
        # Now colorize only the [brackets] and success keywords in the formatted message
        # This preserves colorlog's default formatting for the rest of the line
        # colorlog's RESET codes are preserved to maintain gray/white line colors
        formatted = self._colorize_brackets(formatted)
        
        return formatted


def setup_logging(level: int = logging.INFO, use_colors: bool = True, component_levels: Optional[Dict[str, int]] = None) -> None:
    """
    Setup enhanced logging with color schemes for [brackets] only.
    Preserves colorlog's default gray/white formatting for entire lines.
    
    Args:
        level: Root logging level (default: INFO)
        use_colors: Enable color output (default: True)
        component_levels: Optional dict mapping component names to log levels.
                         Example: {"uvicorn": logging.WARNING, "mcp_controller": logging.WARNING}
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Remove handlers from uvicorn loggers - do this BEFORE setting up our handler
    # This ensures uvicorn doesn't override our logging configuration
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error', 'fastapi', 'mcp_controller']:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.propagate = True
        # Reset level to NOTSET so it inherits from root
        logger.setLevel(logging.NOTSET)
    
    if COLORLOG_AVAILABLE and use_colors:
        # Use sys.stdout to ensure colors work in IntelliJ console
        handler = colorlog.StreamHandler(sys.stdout)
        handler.setFormatter(
            EnhancedColoredFormatter(
                "%(log_color)s%(asctime)s [%(name)s] [%(levelname)s]%(reset)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "white",  # Changed from bold_white - white works better in IntelliJ
                    "WARNING": "yellow",
                    "ERROR": "red",  # Changed from bold_white - red shows errors clearly
                    "CRITICAL": "red,bg_white",
                },
                secondary_log_colors={},
                style="%",
            )
        )
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
        
        # Diagnostic: Log if colorlog is working (only in dev mode)
        if level <= logging.DEBUG:
            test_logger = logging.getLogger("colorlog_test")
            test_logger.debug("Colorlog diagnostic: If you see colors, colorlog is working")
        
        # Configure component loggers with component-specific levels if provided
        component_loggers = {
            'uvicorn': level,
            'uvicorn.access': level,
            'uvicorn.error': logging.WARNING,  # Default: suppress uvicorn.error INFO
            'fastapi': level,
            'mcp_controller': level,
        }
        
        # Override with component-specific levels if provided
        if component_levels:
            for component, comp_level in component_levels.items():
                if component in component_loggers:
                    component_loggers[component] = comp_level
        
        for logger_name, logger_level in component_loggers.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(logger_level)
            logger.propagate = True
    else:
        # Fallback to basic logging
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        root_logger.setLevel(level)
        
        # Apply component-specific levels if provided
        if component_levels:
            for component, comp_level in component_levels.items():
                logger = logging.getLogger(component)
                logger.setLevel(comp_level)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name (default: "agentic_ai")
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name or "agentic_ai")
