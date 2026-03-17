# any-tool

Agent-ready provider API wrappers with typed schemas, OAuth scope mappings, and LLM function-calling definitions.

## What is any-tool?

Provider SDKs are designed for human developers — they expose hundreds or thousands of operations per provider. any-tool adds what agents need:

- **LLM function-calling schemas** — structured tool definitions generated from Pydantic models.
- **Curation** — a selected subset of operations useful for agents, not the entire API surface.
- **Tool-to-scope mappings** — which OAuth scopes each tool requires.
- **Provider quirk handling** — surfaced and handled, not buried in SDK internals.

any-tool defines tools, not transport. The same definitions can be served as MCP, OpenAPI, GraphQL, or plain Python callables. Tool definitions are more durable than wire protocols.

## Installation

```bash
# Core only (tool definitions and schemas, no provider SDK dependencies).

# via uv
uv add any-tool
# via pip
pip install any-tool

# With specific provider extras (installs provider SDK dependencies).

# via uv
uv add any-tool --extra slack --extra google
# via pip
pip install any-tool[slack,google]

# All providers.

# via uv
uv add any-tool --extra all
# via pip
pip install any-tool[all]
```

## Usage

### Discover available tools

```python
from any_tool import discover_tools, get_tools_for_provider

# Discover tools across all installed providers.
# Only providers whose dependencies are installed will be found.
tools = discover_tools()

# Tools for a specific provider.
typeform_tools = get_tools_for_provider("typeform")

for td in typeform_tools:
    print(f"{td.name}: {td.description}")
    print(f"  scopes: {td.scopes}")
    print(f"  docs: {td.api_docs_url}")
```

### Call a tool

```python
from any_tool.providers.typeform.tools import list_forms
from any_tool.providers.typeform.types import ListFormsParams

result = await list_forms(ListFormsParams(page_size=10), token="your-typeform-token")

# Typed attribute access.
for form in result.items:
    print(f"{form.title} ({form.id})")

# LLM-readable string.
print(str(result))

# Dict or JSON.
result.model_dump()
result.model_dump_json()
```

### Access tool metadata

Every tool function decorated with `@tool` has a `_tool_definition` attribute containing its metadata:

```python
from any_tool.providers.typeform.tools import list_forms

td = list_forms._tool_definition
td.name           # "list_forms"
td.provider        # "typeform"
td.scopes          # ["forms:read"]
td.input_schema    # JSON Schema from the Pydantic input model
td.output_schema   # JSON Schema from the Pydantic output model
td.api_docs_url    # "https://www.typeform.com/developers/create/reference/retrieve-forms/"
```

## Adding a provider

Each provider is a directory under `src/any_tool/providers/`:

```
src/any_tool/providers/yourprovider/
├── __init__.py     # Export tool functions
├── types.py        # Pydantic input/output models
├── tools.py        # Async tool functions with @tool decorator
└── scopes.py       # OAuth scope enum and mappings
```

See `src/any_tool/providers/typeform/` for the reference implementation.

### Provider PR checklist

1. Create provider directory with `types.py`, `tools.py`, `scopes.py`, `__init__.py`.
2. Add API docs URLs in `@tool` decorator and provider `__init__.py` docstring.
3. Capture real API response snapshots in `tests/providers/yourprovider/testdata/`.
4. Write tests — model validation, tool function tests (mocked HTTP), contract snapshots.
5. Optionally add integration tests in `test_integration.py`.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
make setup              # Install uv, create venv, sync deps, install pre-commit hooks
make test               # Run unit tests (integration tests skipped by default)
make lint               # Run pre-commit hooks (ruff, ty, detect-secrets)
make test-integration   # Run integration tests (requires provider tokens)
```

Or using uv directly:

```bash
uv sync --group dev     # Sync all dev dependencies
uv run pytest tests     # Run tests
uv run pre-commit run --all-files  # Run linters
```

### Integration tests

Integration tests call real provider APIs and are skipped by default. To run them:

```bash
ANY_TOOL_INTEGRATION_TESTS=1 TYPEFORM_TOKEN=xxx make test-integration
```

## License

[Apache-2.0](LICENSE)
