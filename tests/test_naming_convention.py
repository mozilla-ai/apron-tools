"""Tests to enforce the tool naming convention across all providers."""

from apron_tools import discover_tools


class TestToolNamingConvention:
    """Every tool function name must be prefixed with its provider name."""

    def test_all_tools_prefixed_with_service(self):
        tools = discover_tools()
        assert len(tools) > 0, "No tools discovered."
        violations = []
        for td in tools:
            if not td.name.startswith(f"{td.service}_"):
                violations.append(f"{td.name} (service={td.service}) should start with '{td.service}_'")
        assert not violations, "Tool naming violations:\n" + "\n".join(violations)

    def test_no_duplicate_tool_names(self):
        tools = discover_tools()
        names = [td.name for td in tools]
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, f"Duplicate tool names: {sorted(set(duplicates))}"

    def test_provider_matches_tool_definition(self):
        tools = discover_tools()
        for td in tools:
            assert td.provider, f"Tool {td.name} has empty provider."
            assert td.service, f"Tool {td.name} has empty service."
            assert td.integration, f"Tool {td.name} has empty integration."
            assert td.integration == td.service, f"Tool {td.name} has mismatched integration and service."
            assert td.api_docs_url.startswith("https://"), f"Tool {td.name} has invalid api_docs_url: {td.api_docs_url}"
            assert td.description, f"Tool {td.name} has empty description."
            assert td.input_schema, f"Tool {td.name} has empty input_schema."
            assert td.output_schema, f"Tool {td.name} has empty output_schema."
            assert td.scopes, f"Tool {td.name} has empty scopes."
