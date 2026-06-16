---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 5
  - src/mcp_shell_server/process_manager.py
  - tests/test_process_manager.py
---

# Isolate child process environment

**Change Type**: implementation

## Problem / Context

Child processes currently receive `{**os.environ, **(envs or {})}`. MCP servers are commonly launched with API keys and tokens in the parent environment, so allowed commands or bypass vectors can print secrets into model-visible output.

## Proposed Solution

Build a minimal child environment by default. Only documented allowlisted variables should be inherited or supplied. Secret-like variable names must not be forwarded by default, and audit logging/documentation should redact secret-like metadata.

## Acceptance Criteria

- Child processes do not inherit the full parent environment.
- `SECRET_TOKEN` or similar parent variables are absent from child environment by default.
- A documented allowlist mechanism controls any environment variable inheritance.
- Secret-like variable names are treated defensively in docs and tests.

## Explicit Completion Conditions

- `src/mcp_shell_server/process_manager.py` no longer merges all of `os.environ` into child env.
- Tests prove parent secrets are not visible to children by default.
- README documents child environment isolation and any allowlist configuration.

## Out of Scope

- Secret scanning of the parent process environment beyond child-env isolation and audit redaction.
