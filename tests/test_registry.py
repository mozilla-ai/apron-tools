from any_tool.registry import discover_tools, get_tools_for_provider
from any_tool.types import ToolDefinition


class TestDiscoverTools:
    def test_returns_list(self):
        tools = discover_tools()
        assert isinstance(tools, list)

    def test_all_items_are_tool_definitions(self):
        tools = discover_tools()
        for td in tools:
            assert isinstance(td, ToolDefinition)


class TestGetToolsForProvider:
    def test_unknown_provider_returns_empty(self):
        tools = get_tools_for_provider("nonexistent_provider")
        assert tools == []
