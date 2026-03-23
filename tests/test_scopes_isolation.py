"""Verify scopes are importable without loading tool SDK dependencies."""

import importlib
import pkgutil
import sys

import apron_tools.providers as _providers_pkg
from apron_tools.types import CapabilityGroup

# SDK packages that should NOT be loaded when importing only scopes.
# Only includes packages imported by provider tools.py files, not core
# dependencies like httpx which are always loaded.
SDK_PACKAGES = frozenset(
    {
        "github",
        "slack_sdk",
        "pptx",
        "docx",
    }
)


def _collect_scopes_modules() -> list[str]:
    """Discover all scopes module paths using the same traversal as the registry."""
    modules: list[str] = []
    for _imp, name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
        if not is_pkg:
            continue
        pkg_path = f"apron_tools.providers.{name}"
        pkg = importlib.import_module(pkg_path)
        for _imp2, sub_name, sub_is_pkg in pkgutil.iter_modules(pkg.__path__):
            if sub_name == "scopes" and not sub_is_pkg:
                modules.append(f"{pkg_path}.scopes")
            elif sub_is_pkg:
                sub_pkg_path = f"{pkg_path}.{sub_name}"
                sub_pkg = importlib.import_module(sub_pkg_path)
                for _imp3, leaf_name, leaf_is_pkg in pkgutil.iter_modules(sub_pkg.__path__):
                    if leaf_name == "scopes" and not leaf_is_pkg:
                        modules.append(f"{sub_pkg_path}.scopes")
    return modules


class TestScopesImportIsolation:
    def test_all_scopes_modules_discovered(self):
        """Sanity check — we find all 21 scopes modules."""
        modules = _collect_scopes_modules()
        assert len(modules) >= 21

    def test_importing_scopes_does_not_load_sdks(self):
        """Import every scopes module and verify no SDK packages are loaded."""
        pre_loaded = {pkg for pkg in SDK_PACKAGES if pkg in sys.modules}

        for module_path in _collect_scopes_modules():
            importlib.import_module(module_path)

        newly_loaded = {pkg for pkg in SDK_PACKAGES if pkg in sys.modules and pkg not in pre_loaded}
        assert newly_loaded == set(), f"Importing scopes modules loaded SDK packages: {newly_loaded}"

    def test_every_scopes_module_has_capability_group(self):
        """Every scopes module exports a CAPABILITY_GROUP instance."""
        for module_path in _collect_scopes_modules():
            module = importlib.import_module(module_path)
            cg = getattr(module, "CAPABILITY_GROUP", None)
            assert isinstance(cg, CapabilityGroup), f"{module_path} missing CAPABILITY_GROUP"

    def test_discover_capability_groups_does_not_load_sdks(self):
        """The public API function also avoids loading SDK packages."""
        from apron_tools.registry import discover_capability_groups

        pre_loaded = {pkg for pkg in SDK_PACKAGES if pkg in sys.modules}
        discover_capability_groups()
        newly_loaded = {pkg for pkg in SDK_PACKAGES if pkg in sys.modules and pkg not in pre_loaded}
        assert newly_loaded == set(), f"discover_capability_groups() loaded SDK packages: {newly_loaded}"
