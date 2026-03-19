from pydantic import TypeAdapter

from any_tool.types import (
    CapabilityGroup,
    FileFromBytes,
    FileFromUrl,
    FileInput,
    ToolDefinition,
    ToolResult,
)


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
            service="test",
            integration="test",
            description="A test tool.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            scopes=["read"],
            api_docs_url="https://example.com/docs",
        )
        assert td.name == "test_tool"
        assert td.provider == "test"
        assert td.service == "test"
        assert td.integration == "test"
        assert td.scopes == ["read"]

        try:
            td.name = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass


class TestCapabilityGroup:
    def test_fields(self):
        cg = CapabilityGroup(
            provider="typeform",
            display_name="Typeform",
            scopes=["forms:read", "responses:read"],
        )
        assert cg.provider == "typeform"
        assert cg.display_name == "Typeform"
        assert cg.scopes == ["forms:read", "responses:read"]

    def test_frozen(self):
        cg = CapabilityGroup(
            provider="test",
            display_name="Test",
            scopes=["read"],
        )
        try:
            cg.provider = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass


class TestFileFromBytes:
    def test_fields(self):
        f = FileFromBytes(data=b"hello", filename="test.txt", mime_type="text/plain")
        assert f.type == "bytes"
        assert f.data == b"hello"
        assert f.filename == "test.txt"
        assert f.mime_type == "text/plain"

    def test_type_literal(self):
        f = FileFromBytes(data=b"x", filename="x.bin", mime_type="application/octet-stream")
        assert f.type == "bytes"


class TestFileFromUrl:
    def test_fields(self):
        f = FileFromUrl(url="https://example.com/report.pdf")
        assert f.type == "url"
        assert f.url == "https://example.com/report.pdf"
        assert f.filename is None
        assert f.mime_type is None

    def test_with_overrides(self):
        f = FileFromUrl(url="https://example.com/file", filename="report.pdf", mime_type="application/pdf")
        assert f.filename == "report.pdf"
        assert f.mime_type == "application/pdf"


class TestFileInput:
    def test_discriminated_union_url(self):
        adapter = TypeAdapter(FileInput)
        result = adapter.validate_python({"type": "url", "url": "https://example.com/img.png"})
        assert isinstance(result, FileFromUrl)
        assert result.url == "https://example.com/img.png"

    def test_discriminated_union_bytes(self):
        adapter = TypeAdapter(FileInput)
        result = adapter.validate_python(
            {"type": "bytes", "data": b"raw", "filename": "f.bin", "mime_type": "application/octet-stream"}
        )
        assert isinstance(result, FileFromBytes)
        assert result.data == b"raw"

    def test_json_schema_has_discriminator(self):
        adapter = TypeAdapter(FileInput)
        schema = adapter.json_schema()
        assert "anyOf" in schema or "oneOf" in schema or "discriminator" in schema
