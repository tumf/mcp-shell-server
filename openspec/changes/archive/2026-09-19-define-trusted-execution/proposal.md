---
change_type: implementation
priority: high
dependencies: []
references:
  - README.md
  - SECURITY.md
  - CHANGELOG.md
  - src/mcp_shell_server/server.py
  - tests/test_server.py
verifications:
  - id: trusted-execution-contract
    requirement: Public documentation defines command allowlisting as direct-process authority rather than sandboxing
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: Makefile
    evidence: tests assert the README and SECURITY contracts, the README introductory description no longer claims generic secure execution, and the MCP tool description names the execution boundary
    rerun: uv run pytest -q
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
  - id: runtime-trust-warning
    requirement: Server startup emits a concise warning that allowed programs run with server privileges and require external isolation for untrusted input
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: Makefile
    evidence: tests capture startup logging and assert the warning once without contaminating MCP stdout
    rerun: uv run pytest -q
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
  - id: compatibility-preserved
    requirement: Existing argv execution, command configuration, and defense-in-depth rejections remain operational
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: Makefile
    evidence: the complete test, format, lint, and type-check suite passes without changing command execution configuration
    rerun: uv run pytest -q && uv run black --check . && uv run isort --check . && uv run ruff check . && uv run mypy src/mcp_shell_server tests
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
rollback: Revert the trusted-execution contract commit; no data or wire-format migration is required.
---

# Define the trusted execution security contract

**Change Type**: implementation

## Why

The project is a general-purpose argv execution server, but its current introductory wording and detailed denylist can imply that command allowlisting confines every behavior of an allowed program. Repeated parser mismatches show that program-specific argument filtering cannot be the primary sandbox boundary.

## What Changes

- Define mcp-shell-server as a trusted execution tool: allowing a command delegates that program the server process's existing OS authority.
- State that `ALLOW_COMMANDS` and `ALLOW_PATTERNS` restrict only command names directly launched by the server; they do not guarantee containment of child processes, program-specific interpreters, configuration files, filesystem access, or network access.
- Keep current command-specific rejection rules as best-effort defense in depth. Do not remove or relax existing protections.
- Replace the unqualified “secure shell command execution” description with wording that accurately names the execution boundary.
- Add an operator-facing startup warning through logging/stderr. It must not write to MCP stdout or require a new acknowledgement flag in this compatible release.
- Give concrete external-isolation requirements for untrusted requests or repository contents: least-privilege identity, scoped filesystem, restricted network and credentials, child-process containment, and resource limits.
- Align README, SECURITY.md, runtime tool description, and security-reporting scope with the same threat model.
- Record the operator-visible startup warning and clarified security contract under the changelog's Unreleased section.

## Out of Scope

- Replacing the generic shell tool with fixed Git or filesystem capability APIs.
- Implementing a cross-platform OS sandbox inside this package.
- Removing existing denylist checks or treating documented limitations as immunity for implementation defects.
- Changing MCP tool names, request/response schemas, command configuration variables, or subprocess execution semantics.
- Requiring an explicit acknowledgement environment variable; that remains a possible separately announced major-version change.

## Acceptance

- README and SECURITY.md clearly distinguish direct command-name control from containment of allowed-program behavior.
- Public wording no longer represents the package itself as a complete secure sandbox.
- Documentation states that authenticated or trusted MCP clients do not make model-provided content or repositories trusted.
- External isolation guidance names filesystem, network, credential, descendant-process, and resource boundaries.
- Existing denylist protections remain present and are described as non-exhaustive defense in depth.
- One startup warning is emitted through logging/stderr and MCP stdout framing remains unchanged.
- Existing environment variables and MCP wire behavior remain backward compatible.
- The full repository checks and OpenSpec archive gate pass.
