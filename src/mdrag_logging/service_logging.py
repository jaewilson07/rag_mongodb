"""Global logging configuration for Lambda server.

Provides:
1. dc_logger-based async logging with automatic color coding
2. Correlation ID injection from context
3. Global logger factory functions
4. Log level filtering and configuration

This is the single source of truth for logging in the Lambda server.
All other logging modules should import from here.
"""

import asyncio
import functools
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dc_logger.client.base import (
    Logger,
    get_global_logger,
    get_or_create_logger,
    set_global_logger,
)
from dc_logger.client.extractors import EntityExtractor, ResultProcessor
from dc_logger.client.models import HTTPDetails, LogEntity
from dc_logger.decorators import log_function_call
from fastapi import Request

from .context import get_correlation_id

# ANSI color codes for colored output
_COLOR_CODES = {
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "bold_red": "\033[1;31m",
    "magenta": "\033[35m",
    "blue": "\033[34m",
    "reset": "\033[0m",
}

# Log level hierarchy for filtering
_LEVEL_HIERARCHY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


_VALID_LEVELS = frozenset(_LEVEL_HIERARCHY.keys())


def _normalize_level(level: str) -> str:
    """Normalize and validate level name."""
    normalized = level.upper()
    if normalized not in _VALID_LEVELS:
        valid = ", ".join(sorted(_VALID_LEVELS))
        raise ValueError(f"Invalid log level '{level}'. Valid levels: {valid}")
    return normalized


def colorize(message: str, color: str | None = None) -> str:
    """Apply ANSI color codes to message."""
    if not color or color not in _COLOR_CODES:
        return message
    return f"{_COLOR_CODES[color]}{message}{_COLOR_CODES['reset']}"


class ColoredLogger(Logger):
    """Logger with automatic color coding, level filtering, and correlation ID injection.

    Features:
    - Automatic color by log level (info=green, error=bold_red, etc.)
    - Dynamic log level filtering via set_level() / get_level()
    - Correlation ID injection from context variables
    - Wraps dc_logger instance for async logging

    Example:
        >>> logger = get_logger(__name__)
        >>> await logger.info("Success!")  # Green output with correlation ID
        >>> await logger.error("Failed!")  # Bold red output with correlation ID
    """

    def __init__(
        self,
        base_logger: Logger,
        min_level: str = "INFO",
        debug_color: str | None = "cyan",
        info_color: str | None = "green",
        warning_color: str | None = "yellow",
        error_color: str | None = "bold_red",
        critical_color: str | None = "bold_red",
    ):
        """Initialize ColoredLogger.

        Args:
            base_logger: Underlying Logger instance to wrap
            min_level: Minimum log level to output (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            debug_color: Color for debug messages (default: cyan)
            info_color: Color for info messages (default: green)
            warning_color: Color for warning messages (default: yellow)
            error_color: Color for error messages (default: bold_red)
            critical_color: Color for critical messages (default: bold_red)
        """
        self._logger = base_logger
        normalized_level = _normalize_level(min_level)
        self._min_level = _LEVEL_HIERARCHY[normalized_level]
        self.debug_color = debug_color
        self.info_color = info_color
        self.warning_color = warning_color
        self.error_color = error_color
        self.critical_color = critical_color

    def _should_log(self, level: str) -> bool:
        """Check if message should be logged based on current min_level."""
        return _LEVEL_HIERARCHY.get(level.upper(), 0) >= self._min_level

    def _format_message(self, message: str) -> str:
        """Format message with correlation ID prefix if available."""
        correlation_id = get_correlation_id()
        if correlation_id:
            return f"[{correlation_id}] {message}"
        return message

    async def debug(self, message: str, *args: Any, **context: Any) -> bool:
        """Log debug message with cyan color."""
        if not self._should_log("DEBUG"):
            return False
        formatted_msg = self._format_message(message)
        colored_msg = colorize(formatted_msg, self.debug_color)
        return await self._logger.debug(colored_msg, *args, **context)

    async def info(self, message: str, *args: Any, **context: Any) -> bool:
        """Log info message with green color."""
        if not self._should_log("INFO"):
            return False
        formatted_msg = self._format_message(message)
        colored_msg = colorize(formatted_msg, self.info_color)
        return await self._logger.info(colored_msg, *args, **context)

    async def warning(self, message: str, *args: Any, **context: Any) -> bool:
        """Log warning message with yellow color."""
        if not self._should_log("WARNING"):
            return False
        formatted_msg = self._format_message(message)
        colored_msg = colorize(formatted_msg, self.warning_color)
        return await self._logger.warning(colored_msg, *args, **context)

    async def error(self, message: str, *args: Any, **context: Any) -> bool:
        """Log error message with bold red color."""
        if not self._should_log("ERROR"):
            return False
        formatted_msg = self._format_message(message)
        colored_msg = colorize(formatted_msg, self.error_color)
        return await self._logger.error(colored_msg, *args, **context)

    async def critical(self, message: str, *args: Any, **context: Any) -> bool:
        """Log critical message with bold red color."""
        if not self._should_log("CRITICAL"):
            return False
        formatted_msg = self._format_message(message)
        colored_msg = colorize(formatted_msg, self.critical_color)
        return await self._logger.critical(colored_msg, *args, **context)

    def set_level(self, level: str) -> "ColoredLogger":
        """Set minimum log level dynamically.

        Args:
            level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL

        Returns:
            Self for chaining

        Example:
            >>> logger.set_level("DEBUG")  # Enable debug logs
            >>> logger.set_level("ERROR")  # Only show errors
        """
        normalized_level = _normalize_level(level)
        self._min_level = _LEVEL_HIERARCHY[normalized_level]
        return self

    def get_level(self) -> str:
        """Get current minimum log level.

        Returns:
            Current level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        for name, value in _LEVEL_HIERARCHY.items():
            if value == self._min_level:
                return name
        return "INFO"


# Global logger instance (initialized by setup_logging)
_global_colored_logger: ColoredLogger | None = None


async def setup_logging(log_level: str = "INFO", use_colored: bool = True) -> None:
    """Initialize global logging configuration.

    This function must be called during application startup (e.g., in FastAPI lifespan).
    It configures the global logger with color coding and level filtering.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colored: Whether to use colored output (default: True)

    Example:
        >>> # In FastAPI lifespan
        >>> async def lifespan(app: FastAPI):
        ...     await setup_logging(log_level="INFO")
        ...     yield
    """
    global _global_colored_logger

    base_logger = get_global_logger()

    if use_colored:
        _global_colored_logger = ColoredLogger(
            base_logger=base_logger,
            min_level=log_level,
        )
        set_global_logger(_global_colored_logger)

    else:
        # Use base logger without coloring
        _global_colored_logger = ColoredLogger(
            base_logger=base_logger,
            min_level=log_level,
            debug_color=None,
            info_color=None,
            warning_color=None,
            error_color=None,
            critical_color=None,
        )
        set_global_logger(_global_colored_logger)


def log_async(logger: ColoredLogger, level: str, message: str, **context: Any) -> None:
    """Log from sync context by scheduling async logging.

    Use this helper when you must log from a non-async function.
    """

    level_method = level.lower()
    if level_method not in {"debug", "info", "warning", "error", "critical"}:
        raise ValueError(
            "Invalid log level method. Use one of: debug, info, warning, error, critical"
        )

    async def _do_log() -> None:
        try:
            log_method = getattr(logger, level_method)
            await log_method(message, **context)
        except Exception:
            return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_do_log())
    else:
        loop.create_task(_do_log())


def get_logger(name: str | None = None) -> ColoredLogger:
    """Get a logger instance with color coding and correlation ID support.

    This is the primary function for obtaining loggers throughout the codebase.
    It returns a ColoredLogger instance that automatically includes correlation IDs
    and provides colored output based on log levels.

    Args:
        name: Logger/app name (typically __name__). Used only when creating the
            initial global logger.

    Returns:
        ColoredLogger instance

    Example:
        >>> from utils.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> await logger.info("Processing workflow")  # Green output with correlation ID
    """
    global _global_colored_logger

    # If global logger hasn't been initialized, create a default one
    if _global_colored_logger is None:
        app_name = name or "default_app"
        base_logger = get_or_create_logger(app_name=app_name)
        _global_colored_logger = ColoredLogger(base_logger=base_logger)
        set_global_logger(_global_colored_logger)

    # Return the global logger (all loggers share the same instance for consistency)
    return _global_colored_logger


# ============================================================================
# Logging Decorators and Configuration
# ============================================================================


@dataclass
class LogDecoratorConfig:
    """Configuration for log_call decorator.

    Attributes:
        entity_extractor: Extracts entity info from function parameters
        result_processor: Processes function results for logging

    Example:
        >>> config = LogDecoratorConfig(
        ...     entity_extractor=LambdaEntityExtractor(),
        ...     result_processor=ComfyUIResultProcessor(),
        ... )
        >>> @log_call(config=config)
        ... async def generate_image(...): ...
    """

    entity_extractor: EntityExtractor | None = None
    result_processor: ResultProcessor | None = None


def log_call(
    action_name: str | None = None,
    level_name: str | None = None,
    config: LogDecoratorConfig | None = None,
    logger: Any | None = None,
    **kwargs: Any,
) -> Callable:
    """Enhanced logging decorator with extractors and processors.

    Automatically logs:
    - Function entry/exit with duration
    - Entity information extracted from parameters
    - Formatted and sanitized results
    - HTTP request/response details (if applicable)
    - Errors with full context

    Args:
        action_name: Override action name (defaults to function name)
        level_name: Log level name (e.g., "route", "service", "tool")
        config: LogDecoratorConfig with extractors and processors
        logger: Custom logger instance (optional)
        **kwargs: Additional arguments passed to log_function_call

    Returns:
        Decorated function

    Example:
        >>> from utils.logging import log_call, LogDecoratorConfig
        >>> from utils.logging import LambdaEntityExtractor
        >>> from services.compute.comfyui.logging import ComfyUIResultProcessor
        >>>
        >>> @log_call(
        ...     level_name="route",
        ...     config=LogDecoratorConfig(
        ...         entity_extractor=LambdaEntityExtractor(),
        ...         result_processor=ComfyUIResultProcessor(),
        ...     ),
        ... )
        ... async def generate_image(prompt_id: str, user: User):
        ...     result = await comfyui_client.submit_workflow(workflow_json)
        ...     return result
    """
    # Build decorator kwargs for log_function_call
    decorator_kwargs = {
        "action_name": action_name,
        "logger": logger,
    }

    if level_name:
        decorator_kwargs["level_name"] = level_name

    # Add entity_extractor if provided
    if config and config.entity_extractor:
        decorator_kwargs["entity_extractor"] = config.entity_extractor

    # Add result_processor if provided
    if config and config.result_processor:
        decorator_kwargs["result_processor"] = config.result_processor

    # Add any additional kwargs
    decorator_kwargs.update(kwargs)

    # Remove None values
    decorator_kwargs = {k: v for k, v in decorator_kwargs.items() if v is not None}

    # Apply dc_logger's log_function_call decorator
    return log_function_call(**decorator_kwargs)


def log_route_execution(action: str | None = None):
    """Decorator to log route execution with context.

    Args:
        action: Action name (e.g., "search_documents")

    Example:
        @router.post("/search")
        @log_route_execution(action="search_documents")
        async def search(request: SearchRequest, user: User):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)

            # Extract request and user from kwargs
            request: Request | None = kwargs.get("request")
            user = kwargs.get("user")

            request_id = getattr(request.state, "request_id", None) if request else None
            user_email = user.email if user else None

            # Log start (non-blocking)
            async def log_start():
                try:
                    await logger.info(
                        f"{action or func.__name__} started",
                        request_id=request_id,
                        user_email=user_email,
                        action=action or func.__name__,
                    )
                except Exception:
                    pass

            asyncio.create_task(log_start())

            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start_time) * 1000)

                # Log completion (non-blocking)
                async def log_completion():
                    try:
                        await logger.info(
                            f"{action or func.__name__} completed",
                            request_id=request_id,
                            user_email=user_email,
                            action=action or func.__name__,
                            duration_ms=duration_ms,
                        )
                    except Exception:
                        pass

                asyncio.create_task(log_completion())

                return result

            except Exception as err:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                error = err

                # Log error (non-blocking)
                async def log_error():
                    try:
                        await logger.error(
                            f"{action or func.__name__} failed",
                            request_id=request_id,
                            user_email=user_email,
                            action=action or func.__name__,
                            duration_ms=duration_ms,
                            error=str(error),
                            error_type=type(error).__name__,
                        )
                    except Exception:
                        pass

                asyncio.create_task(log_error())
                raise

        return wrapper

    return decorator


def log_service(action: str | None = None):
    """Decorator for service methods.

    This is a lightweight no-op wrapper used by integrations where
    full structured logging is optional. It preserves compatibility
    with earlier logging utilities.
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def log_service_class(cls):
    """Class decorator for service classes.

    Currently a no-op to keep integrations lightweight and avoid
    hard dependencies in sample scripts.
    """

    return cls


# ============================================================================
# Entity Extractors
# ============================================================================


class LambdaEntityExtractor(EntityExtractor):
    """Extract entity information from Lambda route parameters.

    Supports entity types:
    - workflow: N8n workflows, ComfyUI prompts
    - image: ComfyUI generations, storage paths
    - document: MongoDB documents, Neo4j nodes
    - conversation: Chat messages, Discord interactions
    - user: Authenticated users

    Example:
        >>> extractor = LambdaEntityExtractor()
        >>> entity = extractor.extract(func, args, kwargs)
        >>> print(entity.type)  # "workflow"
        >>> print(entity.id)    # "wf_abc123"
    """

    def extract(self, func: Any, args: tuple, kwargs: dict) -> LogEntity | None:
        """Extract entity from function parameters.

        Args:
            func: Function being called
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            LogEntity or None if no entity found
        """
        func_name = func.__name__.lower()

        # Determine entity type from function name patterns
        if "workflow" in func_name or "n8n" in func_name:
            return self._extract_workflow_entity(kwargs)
        if "image" in func_name or "comfyui" in func_name:
            return self._extract_image_entity(kwargs)
        if "document" in func_name or "rag" in func_name or "mongo" in func_name:
            return self._extract_document_entity(kwargs)
        if "conversation" in func_name or "chat" in func_name:
            return self._extract_conversation_entity(kwargs)
        if "calendar" in func_name or "event" in func_name:
            return self._extract_calendar_entity(kwargs)

        return None

    def _extract_workflow_entity(self, kwargs: dict) -> LogEntity | None:
        """Extract workflow entity (N8n, ComfyUI)."""
        # Try multiple parameter names
        workflow_id = kwargs.get("workflow_id") or kwargs.get("prompt_id") or kwargs.get("id")
        if not workflow_id:
            return None

        user = kwargs.get("user")
        additional_info = {
            "user_email": user.email if user else None,
        }

        # Determine workflow type from ID format
        if isinstance(workflow_id, str):
            if workflow_id.startswith("wf_") or workflow_id.isdigit():
                additional_info["workflow_type"] = "n8n"
            elif len(workflow_id) == 36:  # UUID format
                additional_info["workflow_type"] = "comfyui"

        return LogEntity(
            type="workflow",
            id=str(workflow_id),
            name=f"Workflow {workflow_id}",
            additional_info=additional_info,
        )

    def _extract_image_entity(self, kwargs: dict) -> LogEntity | None:
        """Extract image entity (ComfyUI, storage paths)."""
        # Extract from prompt_id or image path
        prompt_id = kwargs.get("prompt_id")
        image_path = kwargs.get("image_path") or kwargs.get("image_url")

        entity_id = prompt_id or image_path
        if not entity_id:
            return None

        user = kwargs.get("user")
        additional_info = {
            "user_email": user.email if user else None,
            "prompt_id": prompt_id,
            "storage_path": image_path,
        }

        # Extract workflow info if available
        workflow_json = kwargs.get("workflow_json") or kwargs.get("workflow")
        if workflow_json and isinstance(workflow_json, dict):
            additional_info["node_count"] = len(workflow_json)

        # Extract LoRA info
        lora_path = kwargs.get("lora_path")
        if lora_path:
            additional_info["lora_path"] = lora_path

        return LogEntity(
            type="image",
            id=str(entity_id)[:36],  # Truncate long IDs
            name=f"Image {str(entity_id)[:8]}...",
            additional_info=additional_info,
        )

    def _extract_document_entity(self, kwargs: dict) -> LogEntity | None:
        """Extract document entity (MongoDB, Neo4j)."""
        doc_id = kwargs.get("document_id") or kwargs.get("doc_id") or kwargs.get("_id")
        if not doc_id:
            return None

        user = kwargs.get("user")
        additional_info = {
            "user_email": user.email if user else None,
            "collection": kwargs.get("collection"),
            "database": kwargs.get("database"),
        }

        # Add Neo4j-specific info
        if "neo4j" in str(kwargs.get("database", "")).lower():
            additional_info["node_labels"] = kwargs.get("labels")
            additional_info["relationship_type"] = kwargs.get("relationship_type")

        return LogEntity(
            type="document",
            id=str(doc_id),
            name=f"Document {doc_id}",
            additional_info=additional_info,
        )

    def _extract_conversation_entity(self, kwargs: dict) -> LogEntity | None:
        """Extract conversation entity (chat, Discord)."""
        conversation_id = kwargs.get("conversation_id") or kwargs.get("thread_id")
        if not conversation_id:
            return None

        user = kwargs.get("user")
        additional_info = {
            "user_email": user.email if user else None,
            "message_count": len(kwargs.get("messages", [])),
        }

        # Add Discord-specific info
        channel_id = kwargs.get("channel_id")
        if channel_id:
            additional_info["channel_id"] = channel_id
            additional_info["platform"] = "discord"

        return LogEntity(
            type="conversation",
            id=str(conversation_id),
            name=f"Conversation {conversation_id}",
            additional_info=additional_info,
        )

    def _extract_calendar_entity(self, kwargs: dict) -> LogEntity | None:
        """Extract calendar entity (Google Calendar events)."""
        event_id = kwargs.get("event_id") or kwargs.get("calendar_event_id")
        if not event_id:
            return None

        user = kwargs.get("user")
        additional_info = {
            "user_email": user.email if user else None,
            "calendar_id": kwargs.get("calendar_id"),
        }

        # Add event details if available
        event_summary = kwargs.get("summary") or kwargs.get("event_summary")
        if event_summary:
            additional_info["summary"] = event_summary

        return LogEntity(
            type="calendar_event",
            id=str(event_id),
            name=f"Event {event_id}",
            additional_info=additional_info,
        )


# ============================================================================
# Result Processors
# ============================================================================


class HTTPResponseProcessor(ResultProcessor):
    """Generic HTTP response processor with header sanitization.

    Sanitizes sensitive headers:
    - Authorization, X-API-Key, Cookie
    - Cloudflare Access tokens
    - Custom authentication headers

    Truncates large response bodies to 1000 characters.

    Example:
        >>> processor = HTTPResponseProcessor()
        >>> http_details = HTTPDetails(headers={"Authorization": "Bearer secret"})
        >>> context, sanitized_details = processor.process(result, http_details)
        >>> print(sanitized_details.headers["Authorization"])  # "***"
    """

    _SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "cf-access-token",
        "cf-access-jwt-assertion",
        "cookie",
        "set-cookie",
        "x-domo-developer-token",
        "x-auth-token",
    }

    def _sanitize_headers(self, headers: dict) -> dict:
        """Sanitize sensitive headers."""
        if not headers:
            return headers

        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self._SENSITIVE_HEADERS:
                sanitized[key] = "***"
            else:
                sanitized[key] = value
        return sanitized

    def _truncate_body(self, body: Any, max_length: int = 1000) -> Any:
        """Truncate large response bodies."""
        if isinstance(body, str):
            if len(body) > max_length:
                return body[:max_length] + "... (truncated)"
            return body
        if isinstance(body, bytes):
            if len(body) > max_length:
                return body[:max_length] + b"... (truncated)"
            return body
        if isinstance(body, dict | list):
            # Try to serialize and check length
            try:
                serialized = json.dumps(body)
                if len(serialized) > max_length:
                    return f"<Large JSON object, {len(serialized)} chars>"
                return body
            except Exception:
                return body
        return body

    def process(
        self, result: Any, http_details: HTTPDetails | None = None
    ) -> tuple[dict, HTTPDetails | None]:
        """Process HTTP response.

        Args:
            result: Function return value
            http_details: Optional HTTP request/response details

        Returns:
            Tuple of (result_context, http_details)
        """
        result_context = {}

        if http_details:
            # Sanitize request headers
            if http_details.headers:
                http_details.headers = self._sanitize_headers(http_details.headers)

            # Truncate large response bodies
            if http_details.response_body:
                http_details.response_body = self._truncate_body(http_details.response_body)

            # Extract response size if available
            if hasattr(http_details, "response_size"):
                result_context["response_size"] = http_details.response_size

        return result_context, http_details


__all__ = [
    "ColoredLogger",
    "HTTPResponseProcessor",
    "LambdaEntityExtractor",
    "LogDecoratorConfig",
    "get_logger",
    "log_service",
    "log_service_class",
    "log_async",
    "log_call",
    "log_route_execution",
    "setup_logging",
]
