"""Regression tests for project metadata.

The server is written against the MCP Python SDK v1 low-level ``Server`` API
(``@app.list_tools()``). Resolving SDK 2.x crashes the package at import time,
so the declared dependency must keep an upper bound while that API is in use.
The decision logic lives in the pure helpers below so it can be verified with
in-memory inputs; the repository-facing tests apply those helpers to the
committed metadata files.
"""

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
LOCKFILE = PROJECT_ROOT / "uv.lock"
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"
SERVER_SOURCE = PROJECT_ROOT / "src" / "mcp_shell_server" / "server.py"

MCP_V2 = Version("2.0.0")


def find_requirement(dependencies: list[str], name: str) -> str:
    """Return the raw requirement string for ``name``."""
    for dependency in dependencies:
        if Requirement(dependency).name == name:
            return dependency
    raise AssertionError(f"no {name!r} requirement declared in {dependencies!r}")


def permits_version(requirement: str, version: Version) -> bool:
    """Report whether ``requirement`` allows ``version`` to be resolved."""
    return version in SpecifierSet(str(Requirement(requirement).specifier))


def uses_v1_low_level_api(source: str) -> bool:
    """Report whether ``source`` still uses the SDK v1 low-level server API."""
    return "from mcp.server import Server" in source and "@app.list_tools()" in source


def changelog_records_mcp_v2_fix(changelog: str) -> bool:
    """Report whether the changelog documents the MCP SDK 2.x startup fix."""
    for line in changelog.splitlines():
        lowered = line.strip().lower()
        if not lowered.startswith("-"):
            continue
        if "mcp" in lowered and ("2.x" in lowered or "2.0" in lowered):
            return True
    return False


def locked_version(lock: dict, name: str) -> Version:
    """Return the version ``name`` resolves to in a parsed ``uv.lock``."""
    for package in lock["package"]:
        if package["name"] == name:
            return Version(package["version"])
    raise AssertionError(f"{name!r} is missing from the lockfile")


@pytest.mark.parametrize(
    "requirement,permitted",
    [
        ("mcp>=1.1.2", True),
        ("mcp", True),
        ("mcp>=2.0.0", True),
        ("mcp>=1.1.2,<2", False),
        ("mcp>=1.1.2,<2.0.0", False),
        ("mcp~=1.1", False),
        ("mcp==1.27.2", False),
    ],
)
def test_permits_version_detects_v2_exposure(requirement: str, permitted: bool) -> None:
    assert permits_version(requirement, MCP_V2) is permitted


def test_find_requirement_selects_the_named_dependency() -> None:
    assert find_requirement(["h11>=0.16.0", "mcp>=1.1.2,<2"], "mcp") == "mcp>=1.1.2,<2"


def test_find_requirement_rejects_a_missing_dependency() -> None:
    with pytest.raises(AssertionError):
        find_requirement(["h11>=0.16.0"], "mcp")


def test_uses_v1_low_level_api_detects_the_v1_markers() -> None:
    v1 = "from mcp.server import Server\n\n@app.list_tools()\nasync def f(): ...\n"
    assert uses_v1_low_level_api(v1) is True
    assert uses_v1_low_level_api("from mcp.server import FastMCP\n") is False


def test_changelog_records_mcp_v2_fix_matches_only_entry_lines() -> None:
    assert changelog_records_mcp_v2_fix("- Pin the MCP SDK below 2.x.\n") is True
    assert changelog_records_mcp_v2_fix("## MCP SDK 2.x\n") is False
    assert changelog_records_mcp_v2_fix("- Unrelated fix.\n") is False


def test_locked_version_reads_the_resolved_package() -> None:
    lock = {"package": [{"name": "mcp", "version": "1.27.2"}]}
    assert locked_version(lock, "mcp") == Version("1.27.2")


def test_pyproject_excludes_mcp_v2() -> None:
    """The declared dependency must not resolve SDK 2.x while v1 APIs are used."""
    if not uses_v1_low_level_api(SERVER_SOURCE.read_text()):
        pytest.skip("server no longer uses the MCP SDK v1 low-level API")

    dependencies = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    requirement = find_requirement(dependencies, "mcp")
    assert not permits_version(requirement, MCP_V2), (
        f"{requirement!r} permits MCP SDK 2.x, which crashes the server at import; "
        "keep the upper bound until the server migrates off the v1 low-level API"
    )


def test_lockfile_resolves_mcp_v1() -> None:
    resolved = locked_version(tomllib.loads(LOCKFILE.read_text()), "mcp")
    assert resolved < MCP_V2, f"uv.lock resolves mcp {resolved}, expected a 1.x release"


def test_changelog_records_mcp_v2_compatibility_fix() -> None:
    assert changelog_records_mcp_v2_fix(
        CHANGELOG.read_text()
    ), "CHANGELOG.md must record the MCP SDK 2.x startup-crash fix"
