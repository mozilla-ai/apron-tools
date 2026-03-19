import asyncio

from pydantic import BaseModel

from any_tool.tool import tool
from any_tool.types import ToolDefinition, ToolResult


class DummyParams(BaseModel):
    query: str
    limit: int = 10


class DummyResult(ToolResult):
    items: list[str]

    def __str__(self) -> str:
        return f"Found {len(self.items)} items."


class TestToolDecorator:
    def test_attaches_tool_definition(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs/list")
        async def list_things(params: DummyParams, *, token: str) -> DummyResult:
            """List all things."""
            ...

        assert hasattr(list_things, "_tool_definition")
        td = list_things._tool_definition
        assert isinstance(td, ToolDefinition)

    def test_extracts_name(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """My tool description."""
            ...

        assert my_tool._tool_definition.name == "my_tool"

    def test_extracts_description_from_docstring(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """My tool description."""
            ...

        assert my_tool._tool_definition.description == "My tool description."

    def test_extracts_scopes(self):
        @tool(scopes=["forms:read", "forms:write"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        assert my_tool._tool_definition.scopes == ["forms:read", "forms:write"]

    def test_extracts_api_docs_url(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs/endpoint")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        assert my_tool._tool_definition.api_docs_url == "https://example.com/docs/endpoint"

    def test_extracts_input_schema(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        schema = my_tool._tool_definition.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]

    def test_extracts_output_schema(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        schema = my_tool._tool_definition.output_schema
        assert schema["type"] == "object"
        assert "items" in schema["properties"]

    def test_extracts_provider_from_kwarg(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs", provider="custom")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        assert my_tool._tool_definition.provider == "custom"
        assert my_tool._tool_definition.service == "custom"
        assert my_tool._tool_definition.integration == "custom"

    def test_service_defaults_to_provider(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs", provider="slack")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        assert my_tool._tool_definition.provider == "slack"
        assert my_tool._tool_definition.service == "slack"
        assert my_tool._tool_definition.integration == "slack"

    def test_explicit_service(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs", provider="google", service="google_sheets")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        assert my_tool._tool_definition.provider == "google"
        assert my_tool._tool_definition.service == "google_sheets"
        assert my_tool._tool_definition.integration == "google_sheets"

    def test_function_remains_callable(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            return DummyResult(success=True, items=["a", "b"])

        result = asyncio.run(my_tool(DummyParams(query="test"), token="tok"))
        assert result.success is True
        assert result.items == ["a", "b"]

    def test_preserves_function_name_and_docstring(self):
        @tool(scopes=["read"], api_docs="https://example.com/docs")
        async def my_tool(params: DummyParams, *, token: str) -> DummyResult:
            """A tool."""
            ...

        assert my_tool.__name__ == "my_tool"
        assert my_tool.__doc__ == "A tool."
