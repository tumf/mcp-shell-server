"""Regression tests for MCP SDK compatibility metadata."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_mcp_v2_is_excluded_while_server_uses_v1_api() -> None:
    server = (ROOT / "src/mcp_shell_server/server.py").read_text()
    if "@app.list_tools()" not in server:
        return

    dependencies = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "dependencies"
    ]
    mcp_requirement = next(item for item in dependencies if item.startswith("mcp"))
    assert mcp_requirement.endswith(",<2")


def test_lockfile_resolves_mcp_v1() -> None:
    packages = tomllib.loads((ROOT / "uv.lock").read_text())["package"]
    mcp = next(package for package in packages if package["name"] == "mcp")
    assert mcp["version"].startswith("1.")
