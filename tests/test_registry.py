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


class TestDiscoverToolsWithTypeform:
    def test_discovers_typeform_tools(self):
        tools = discover_tools()
        names = [td.name for td in tools]
        assert "list_forms" in names
        assert "get_form" in names
        assert "get_responses" in names

    def test_typeform_tools_have_correct_provider(self):
        tools = discover_tools()
        typeform_tools = [td for td in tools if td.provider == "typeform"]
        assert len(typeform_tools) == 3

    def test_typeform_tools_have_scopes(self):
        tools = discover_tools()
        typeform_tools = [td for td in tools if td.provider == "typeform"]
        for td in typeform_tools:
            assert len(td.scopes) > 0

    def test_typeform_tools_have_schemas(self):
        tools = discover_tools()
        typeform_tools = [td for td in tools if td.provider == "typeform"]
        for td in typeform_tools:
            assert td.input_schema
            assert td.output_schema

    def test_typeform_tools_have_api_docs(self):
        tools = discover_tools()
        typeform_tools = [td for td in tools if td.provider == "typeform"]
        for td in typeform_tools:
            assert td.api_docs_url.startswith("https://")


class TestGetToolsForProvider:
    def test_unknown_provider_returns_empty(self):
        tools = get_tools_for_provider("nonexistent_provider")
        assert tools == []

    def test_returns_typeform_tools(self):
        tools = get_tools_for_provider("typeform")
        assert len(tools) == 3

    def test_excludes_other_providers(self):
        tools = get_tools_for_provider("typeform")
        for td in tools:
            assert td.provider == "typeform"
