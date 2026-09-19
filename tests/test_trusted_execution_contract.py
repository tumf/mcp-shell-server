"""Contract tests for the trusted-execution security definition.

These bind the public documentation, the MCP tool description, and the startup
warning to one threat model: allowing a command delegates the server process's
OS authority to that program, and the allowlist controls only the executable
names the server launches directly.
"""

import logging
import sys
from pathlib import Path

import pytest

from mcp_shell_server.server import (
    TRUSTED_EXECUTION_WARNING,
    ExecuteToolHandler,
    emit_trusted_execution_warning,
)

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text()
SECURITY = (ROOT / "SECURITY.md").read_text()
CHANGELOG = (ROOT / "CHANGELOG.md").read_text()

# Wording that would present the package itself as a complete secure sandbox.
UNQUALIFIED_SANDBOX_CLAIMS = (
    "A secure shell command execution server",
    "secure shell command execution server",
)

# Every external boundary the documentation must require of the deployment.
EXTERNAL_ISOLATION_BOUNDARIES = (
    "least-privilege",
    "filesystem",
    "network",
    "credential",
    "descendant-process",
    "resource limits",
)


def _unreleased_section(changelog: str) -> str:
    """Return the text between the Unreleased heading and the next release."""
    _, _, after = changelog.partition("## [Unreleased]")
    assert after, "CHANGELOG.md has no Unreleased section"
    body, _, _ = after.partition("\n## [")
    return body


class TestReadmeContract:
    def test_readme_makes_no_unqualified_complete_sandbox_claim(self) -> None:
        for claim in UNQUALIFIED_SANDBOX_CLAIMS:
            assert claim not in README, f"README still claims: {claim!r}"

    def test_readme_introduction_names_the_execution_boundary(self) -> None:
        # The claim must appear before any configuration example.
        intro = README.partition("## MCP client setting")[0]
        assert "trusted execution" in intro.lower()
        assert "not a sandbox" in intro.lower()
        assert "Trusted execution contract" in intro

    def test_readme_scopes_allowlists_to_directly_launched_names(self) -> None:
        contract = README.partition("## Trusted execution contract")[2].partition(
            "## MCP client setting"
        )[0]
        assert contract, "README has no Trusted execution contract section"
        assert "`ALLOW_COMMANDS` and `ALLOW_PATTERNS` restrict only" in contract
        assert "launches directly" in contract
        for uncontained in (
            "child processes",
            "interpreters",
            "configuration files",
            "filesystem",
            "network access",
        ):
            assert uncontained in contract, f"README omits {uncontained!r}"

    def test_readme_keeps_hardening_as_non_exhaustive_defense_in_depth(self) -> None:
        assert "defense in depth" in README
        assert "non-exhaustive" in README.lower()
        # The existing command-specific rejection rules stay documented.
        for rule in ("find -exec", "awk system()", "--compress-program", "git -c"):
            assert rule in README, f"README dropped the {rule!r} rejection rule"

    def test_readme_requires_concrete_external_isolation(self) -> None:
        contract = README.partition("## Trusted execution contract")[2].partition(
            "## MCP client setting"
        )[0]
        lowered = contract.lower()
        for boundary in EXTERNAL_ISOLATION_BOUNDARIES:
            assert boundary in lowered, f"README omits the {boundary!r} boundary"

    def test_readme_states_trusted_client_does_not_trust_content(self) -> None:
        contract = README.partition("## Trusted execution contract")[2].partition(
            "## MCP client setting"
        )[0]
        assert "does not make the" in contract
        assert "untrusted input" in contract


class TestSecurityPolicyContract:
    def test_security_policy_makes_no_unqualified_complete_sandbox_claim(self) -> None:
        for claim in UNQUALIFIED_SANDBOX_CLAIMS:
            assert claim not in SECURITY, f"SECURITY.md still claims: {claim!r}"
        assert "not a sandbox" in SECURITY

    def test_security_policy_separates_guarantees_from_non_guarantees(self) -> None:
        assert "### Guarantees" in SECURITY
        assert "### Non-guarantees" in SECURITY
        non_guarantees = SECURITY.partition("### Non-guarantees")[2].partition(
            "### Defense in depth"
        )[0]
        assert non_guarantees.strip(), "SECURITY.md has an empty Non-guarantees section"
        for uncontained in (
            "child",
            "network access",
            "filesystem",
            "credential",
        ):
            assert uncontained in non_guarantees, f"Non-guarantees omit {uncontained!r}"

    def test_security_policy_defines_authority_delegation(self) -> None:
        model = SECURITY.partition("## Security Model")[2]
        assert "delegates" in model
        assert "OS authority" in model
        assert "launches directly" in model

    def test_security_policy_states_trusted_client_does_not_trust_content(self) -> None:
        assert (
            "does not make the content it processes trusted" in SECURITY
        ), "SECURITY.md must distinguish a trusted connection from trusted content"

    def test_security_policy_keeps_hardening_as_non_exhaustive(self) -> None:
        defense = SECURITY.partition("### Defense in depth")[2].partition(
            "### Audit logging"
        )[0]
        assert "non-exhaustive" in defense
        for rule in ("find -exec", "awk system()", "--compress-program", "git -c"):
            assert rule in defense, f"SECURITY.md dropped the {rule!r} rejection rule"

    def test_security_policy_requires_concrete_external_isolation(self) -> None:
        guidance = SECURITY.partition("## Deployment guidance")[2]
        assert guidance, "SECURITY.md has no Deployment guidance section"
        lowered = guidance.lower()
        for boundary in EXTERNAL_ISOLATION_BOUNDARIES:
            assert boundary in lowered, f"SECURITY.md omits the {boundary!r} boundary"

    def test_reporting_scope_retains_enforced_boundary_reports(self) -> None:
        scope = SECURITY.partition("### Reporting scope")[2].partition(
            "## Security Model"
        )[0]
        assert scope, "SECURITY.md has no Reporting scope section"
        assert "never waives security treatment" in scope
        for sensitive in (
            "allowlist",
            "shell interpretation",
            "redirection",
            "secrets",
            "execution limits",
            "audit",
        ):
            assert sensitive in scope, f"Reporting scope omits {sensitive!r}"


class TestChangelogContract:
    def test_unreleased_records_the_startup_warning_and_contract(self) -> None:
        unreleased = _unreleased_section(CHANGELOG)
        assert "startup" in unreleased
        assert "warning" in unreleased
        assert "trusted-execution" in unreleased
        assert "SECURITY.md" in unreleased


class TestStartupWarning:
    def test_warning_text_states_the_contract(self) -> None:
        text = TRUSTED_EXECUTION_WARNING
        assert "ALLOW_COMMANDS" in text
        assert "ALLOW_PATTERNS" in text
        assert "authority" in text
        assert "untrusted" in text
        assert "isolation" in text

    def test_warning_is_emitted_at_warning_level(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="mcp-shell-server"):
            emit_trusted_execution_warning()

        records = [
            record
            for record in caplog.records
            if record.getMessage() == TRUSTED_EXECUTION_WARNING
        ]
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING

    def test_warning_does_not_write_to_stdout(self, capsys) -> None:
        emit_trusted_execution_warning()
        assert capsys.readouterr().out == ""

    def test_no_log_handler_targets_stdout(self) -> None:
        # MCP stdio framing owns stdout; logging must stay on stderr.
        streams = []
        current: logging.Logger | None = logging.getLogger("mcp-shell-server")
        while current is not None:
            for handler in current.handlers:
                stream = getattr(handler, "stream", None)
                if stream is not None:
                    streams.append(stream)
            current = current.parent if current.propagate else None

        assert sys.stdout not in streams
        assert sys.__stdout__ not in streams

    @pytest.mark.asyncio
    async def test_main_emits_the_warning_once(self, mocker, caplog) -> None:
        from mcp_shell_server.server import main

        context_manager = mocker.AsyncMock()
        context_manager.__aenter__ = mocker.AsyncMock(
            return_value=(mocker.AsyncMock(), mocker.AsyncMock())
        )
        context_manager.__aexit__ = mocker.AsyncMock(return_value=None)
        mocker.patch(
            "mcp.server.stdio.stdio_server",
            mocker.Mock(side_effect=lambda: context_manager),
        )
        mocker.patch("mcp_shell_server.server.app.run")
        mocker.patch("mcp_shell_server.server.app.create_initialization_options")

        with caplog.at_level(logging.WARNING, logger="mcp-shell-server"):
            await main()

        emitted = [
            record
            for record in caplog.records
            if record.getMessage() == TRUSTED_EXECUTION_WARNING
        ]
        assert len(emitted) == 1

    @pytest.mark.asyncio
    async def test_main_keeps_stdout_free_of_warning_text(self, mocker, capsys) -> None:
        from mcp_shell_server.server import main

        context_manager = mocker.AsyncMock()
        context_manager.__aenter__ = mocker.AsyncMock(
            return_value=(mocker.AsyncMock(), mocker.AsyncMock())
        )
        context_manager.__aexit__ = mocker.AsyncMock(return_value=None)
        mocker.patch(
            "mcp.server.stdio.stdio_server",
            mocker.Mock(side_effect=lambda: context_manager),
        )
        mocker.patch("mcp_shell_server.server.app.run")
        mocker.patch("mcp_shell_server.server.app.create_initialization_options")

        await main()

        assert capsys.readouterr().out == ""


class TestToolDescriptionContract:
    def test_tool_description_names_the_execution_boundary(self, monkeypatch) -> None:
        monkeypatch.setenv("ALLOW_COMMANDS", "echo")
        tool = ExecuteToolHandler().get_tool_description()

        assert tool.name == "shell_execute"
        description = tool.description or ""
        assert "server process's OS authority" in description
        assert "not what an allowed program does" in description

    def test_tool_contract_is_backward_compatible(self, monkeypatch) -> None:
        monkeypatch.setenv("ALLOW_COMMANDS", "echo")
        tool = ExecuteToolHandler().get_tool_description()

        assert tool.inputSchema["type"] == "object"
        assert set(tool.inputSchema["properties"]) == {
            "command",
            "stdin",
            "directory",
            "timeout",
        }
        assert tool.inputSchema["required"] == ["command"]
