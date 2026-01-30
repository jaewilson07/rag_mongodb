"""Service logging decorators using standard logging."""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])


def _build_action(func_name: str, status: str) -> str:
    return f"{func_name}_service_{status}"


@overload
def log_service(func: F) -> F: ...


@overload
def log_service(*, entity_type: str = "service") -> Callable[[F], F]: ...


def log_service(func: F | None = None, *, entity_type: str = "service") -> F | Callable[[F], F]:
    """Log service calls at debug level for entry and error.

    Works for both async and sync callables.
    """

    def decorator(target: F) -> F:
        logger = logging.getLogger(target.__module__)
        func_name = target.__qualname__

        if inspect.iscoroutinefunction(target):

            @functools.wraps(target)
            async def async_wrapper(*args: Any, **kwargs: Any):
                logger.debug(
                    "Service call started",
                    extra={
                        "action": _build_action(func_name, "start"),
                        "entity_type": entity_type,
                        "service": func_name,
                    },
                )
                try:
                    return await target(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - passthrough
                    logger.debug(
                        "Service call failed",
                        extra={
                            "action": _build_action(func_name, "error"),
                            "entity_type": entity_type,
                            "service": func_name,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                    raise

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(target)
        def sync_wrapper(*args: Any, **kwargs: Any):
            logger.debug(
                "Service call started",
                extra={
                    "action": _build_action(func_name, "start"),
                    "entity_type": entity_type,
                    "service": func_name,
                },
            )
            try:
                return target(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - passthrough
                logger.debug(
                    "Service call failed",
                    extra={
                        "action": _build_action(func_name, "error"),
                        "entity_type": entity_type,
                        "service": func_name,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                raise

        return sync_wrapper  # type: ignore[return-value]

    if func is None:
        return decorator

    return decorator(func)


def log_service_class(cls: type[Any]) -> type[Any]:
    """Apply log_service to all public methods in a service class."""

    for name, value in list(cls.__dict__.items()):
        if name.startswith("_"):
            continue
        if isinstance(value, staticmethod):
            setattr(cls, name, staticmethod(log_service(value.__func__)))
            continue
        if isinstance(value, classmethod):
            setattr(cls, name, classmethod(log_service(value.__func__)))
            continue
        if not callable(value):
            continue
        setattr(cls, name, log_service(value))
    return cls
