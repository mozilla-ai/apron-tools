from apron_tools.registry import (
    discover_capability_groups,
    discover_tools,
    get_tools_for_provider,
    get_tools_for_service,
)
from apron_tools.types import CapabilityGroup, ToolDefinition


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
        assert "typeform_explore_workspace" in names
        assert "typeform_get_form_details" in names
        assert "typeform_get_form_responses" in names

    def test_typeform_tools_have_correct_provider(self):
        tools = discover_tools()
        typeform_tools = [td for td in tools if td.provider == "typeform"]
        assert len(typeform_tools) == 5

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


class TestDiscoverToolsStructure:
    """Verify discovery works across flat and hierarchical provider structures."""

    def test_discovers_flat_provider_tools(self):
        tools = discover_tools()
        names = {td.name for td in tools}
        assert "github_get_issue" in names
        assert "slack_send_channel_message" in names

    def test_discovers_hierarchical_provider_tools(self):
        tools = discover_tools()
        names = {td.name for td in tools}
        assert "google_sheets_list_spreadsheets" in names
        assert "gmail_list_emails" in names
        assert "microsoft_teams_list_chats" in names
        assert "atlassian_jira_explore_projects" in names

    def test_discovers_optional_provider_tools(self):
        """PowerPoint and Word tools are optional — discovered when installed."""
        tools = discover_tools()
        names = {td.name for td in tools}
        assert "microsoft_powerpoint_read_presentation" in names
        assert "microsoft_word_read_document" in names


class TestGetToolsForProvider:
    def test_unknown_provider_returns_empty(self):
        tools = get_tools_for_provider("nonexistent_provider")
        assert tools == []

    def test_returns_typeform_tools(self):
        tools = get_tools_for_provider("typeform")
        assert len(tools) == 5

    def test_excludes_other_providers(self):
        tools = get_tools_for_provider("typeform")
        for td in tools:
            assert td.provider == "typeform"

    def test_google_provider_returns_all_google_services(self):
        tools = get_tools_for_provider("google")
        assert len(tools) > 0
        services = {td.service for td in tools}
        assert "google_sheets" in services
        assert "gmail" in services
        assert "google_drive" in services
        assert "google_calendar" in services
        assert "google_docs" in services
        assert "google_slides" in services
        for td in tools:
            assert td.provider == "google"

    def test_atlassian_provider_returns_jira_and_confluence(self):
        tools = get_tools_for_provider("atlassian")
        assert len(tools) > 0
        services = {td.service for td in tools}
        assert "atlassian_jira" in services
        assert "atlassian_confluence" in services
        for td in tools:
            assert td.provider == "atlassian"

    def test_microsoft_provider_returns_teams_and_excel(self):
        tools = get_tools_for_provider("microsoft")
        assert len(tools) > 0
        services = {td.service for td in tools}
        assert "microsoft_teams" in services
        assert "microsoft_excel" in services
        for td in tools:
            assert td.provider == "microsoft"


class TestGetToolsForService:
    def test_unknown_service_returns_empty(self):
        tools = get_tools_for_service("nonexistent_service")
        assert tools == []

    def test_returns_google_sheets_tools(self):
        tools = get_tools_for_service("google_sheets")
        assert len(tools) > 0
        for td in tools:
            assert td.service == "google_sheets"
            assert td.provider == "google"

    def test_returns_gmail_tools(self):
        tools = get_tools_for_service("gmail")
        assert len(tools) > 0
        for td in tools:
            assert td.service == "gmail"
            assert td.provider == "google"

    def test_returns_atlassian_jira_tools(self):
        tools = get_tools_for_service("atlassian_jira")
        assert len(tools) > 0
        for td in tools:
            assert td.service == "atlassian_jira"
            assert td.provider == "atlassian"

    def test_standalone_provider_service_matches(self):
        tools = get_tools_for_service("typeform")
        assert len(tools) == 5
        for td in tools:
            assert td.service == "typeform"
            assert td.provider == "typeform"


class TestDiscoverCapabilityGroups:
    def test_returns_list(self):
        groups = discover_capability_groups()
        assert isinstance(groups, list)

    def test_all_items_are_capability_groups(self):
        groups = discover_capability_groups()
        for cg in groups:
            assert isinstance(cg, CapabilityGroup)

    def test_discovers_flat_providers(self):
        groups = discover_capability_groups()
        providers = {cg.provider for cg in groups}
        assert "github" in providers
        assert "slack" in providers
        assert "typeform" in providers

    def test_discovers_hierarchical_providers(self):
        groups = discover_capability_groups()
        providers = {cg.provider for cg in groups}
        assert "gmail" in providers
        assert "google_sheets" in providers
        assert "microsoft_teams" in providers
        assert "atlassian_jira" in providers

    def test_each_group_has_scopes(self):
        groups = discover_capability_groups()
        for cg in groups:
            assert len(cg.scopes) > 0, f"{cg.provider} has no scopes"

    def test_each_group_has_display_name(self):
        groups = discover_capability_groups()
        for cg in groups:
            assert cg.display_name, f"{cg.provider} has no display_name"
