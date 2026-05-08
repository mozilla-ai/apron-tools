"""The @tool decorator for registering tool functions."""

from __future__ import annotations

import typing
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from apron_tools.types import ToolDefinition


def tool(
    *,
    scopes: Sequence[str],
    api_docs: str,
    provider: str = "",
    service: str = "",
) -> Any:
    """Decorate a tool function to attach a ToolDefinition.

    The decorator extracts metadata from the function's type hints and
    docstring, builds a ``ToolDefinition``, and attaches it as
    ``func._tool_definition``. The function itself is not wrapped —
    it remains directly callable.

    Args:
        scopes: OAuth scopes required to call this tool.
        api_docs: URL to the provider API documentation for this endpoint.
        provider: OAuth provider name (e.g. ``google``, ``slack``).
        service: Specific product name (e.g. ``google_sheets``). Defaults
            to ``provider`` for standalone providers.

    Raises:
        TypeError: If the decorated function lacks a ``params`` argument
            annotated with a Pydantic ``BaseModel`` subclass.
    """

    def decorator(func: Any) -> Any:
        # ``typing.get_type_hints`` resolves PEP 563 string annotations to
        # real classes, which is what consumers downstream of
        # ``ToolDefinition.params_class`` rely on. ``inspect.signature``
        # would return the raw string annotation here.
        hints = typing.get_type_hints(func)
        params_type = hints.get("params")
        return_type = hints.get("return")

        if not (isinstance(params_type, type) and issubclass(params_type, BaseModel)):
            raise TypeError(
                f"@tool function {func.__name__!r} must declare a 'params' argument "
                "annotated with a Pydantic BaseModel subclass.",
            )

        input_schema = params_type.model_json_schema()

        output_schema: dict[str, Any] = {}
        if return_type is not None and hasattr(return_type, "model_json_schema"):
            output_schema = return_type.model_json_schema()

        description = (func.__doc__ or "").strip().split("\n")[0]

        resolved_service = service or provider

        func._tool_definition = ToolDefinition(
            name=func.__name__,
            provider=provider,
            service=resolved_service,
            integration=resolved_service,
            description=description,
            params_class=params_type,
            input_schema=input_schema,
            output_schema=output_schema,
            scopes=list(scopes),
            api_docs_url=api_docs,
        )

        return func

    return decorator
