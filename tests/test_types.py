from any_tool.types import ToolDefinition, ToolResult


class TestToolResult:
    def test_success_result_fields(self):
        class ConcreteResult(ToolResult):
            message: str

            def __str__(self) -> str:
                return self.message

        result = ConcreteResult(success=True, message="it worked")
        assert result.success is True
        assert result.error is None
        assert result.message == "it worked"
        assert str(result) == "it worked"

    def test_error_result_fields(self):
        class ConcreteResult(ToolResult):
            message: str = ""

            def __str__(self) -> str:
                return self.error or self.message

        result = ConcreteResult(success=False, error="something broke")
        assert result.success is False
        assert result.error == "something broke"
        assert str(result) == "something broke"

    def test_base_str_raises(self):
        class NoStrResult(ToolResult):
            pass

        result = NoStrResult(success=True)
        try:
            str(result)
            raise AssertionError("Expected NotImplementedError")
        except NotImplementedError:
            pass

    def test_model_dump(self):
        class ConcreteResult(ToolResult):
            value: int

            def __str__(self) -> str:
                return f"value={self.value}"

        result = ConcreteResult(success=True, value=42)
        data = result.model_dump()
        assert data["success"] is True
        assert data["value"] == 42
        assert data["error"] is None


class TestToolDefinition:
    def test_frozen(self):
        td = ToolDefinition(
            name="test_tool",
            provider="test",
            description="A test tool.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            scopes=["read"],
            api_docs_url="https://example.com/docs",
        )
        assert td.name == "test_tool"
        assert td.provider == "test"
        assert td.scopes == ["read"]

        try:
            td.name = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass
