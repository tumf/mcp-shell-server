---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-56qh-7rgp-wfgr
  - src/mcp_shell_server/command_validator.py
  - tests/test_command_validator.py
  - tests/test_shell_executor.py
  - SECURITY.md
---

# Reject Git Command-Scoped Configuration Overrides

**Change Type**: implementation

## Problem / Context

An allowlisted `git` command accepts command-scoped configuration through `-c <name=value>` and `-c<name=value>`. Git has multiple configuration keys whose values launch external programs. The current key-specific denylist is incomplete, allowing configurations such as `core.fsmonitor` and `diff.external` to execute arbitrary host commands despite the command allowlist.

Enumerating executable Git configuration keys is not a durable security boundary because Git can add or reinterpret such keys. The safe minimal policy is to reject all command-scoped Git configuration overrides before subprocess creation.

## Proposed Solution

- Reject every `git -c <name=value>` and `git -c<name=value>` invocation regardless of the configuration key or value.
- Remove the key-specific Git configuration classification that implies selected `-c` values are safe.
- Preserve existing rejection of external-program options and `ext::` transports.
- Preserve ordinary allowlisted Git commands that do not use command-scoped configuration.
- Update security documentation to state the conservative `git -c` boundary.
- Add validator and executor-level regressions proving known payloads are rejected before execution.
- Prepare release/advisory metadata identifying versions through `1.1.1` as affected and the next release as patched.

This remains one proposal because validation, runtime enforcement, regression coverage, documentation, and patched-release metadata form one atomic security fix.

## Acceptance Criteria

- `git -c core.fsmonitor=touch marker status` is rejected before subprocess creation and does not create `marker`.
- `git -cdiff.external=touch marker diff --ext-diff` is rejected before subprocess creation and does not create `marker`.
- Benign-looking command-scoped configuration such as `git -c user.name=Example status` is also rejected.
- Existing Git alias, external-program option, and `ext::` transport bypass cases remain rejected.
- `git status` remains allowed when `git` is allowlisted.
- Security documentation no longer claims or implies that selected `git -c` configuration is safe.
- Automated tests, lint, and type checking pass using the repository-provided commands.
- The security advisory records `<=1.1.1` as vulnerable and the next published package version as patched before publication.

## Explicit Completion Conditions

- `src/mcp_shell_server/command_validator.py` contains a value-independent rejection path for both supported `git -c` argument forms and no longer relies on a Git configuration-key denylist.
- `tests/test_command_validator.py` covers both separated and attached `-c` forms, malicious examples, benign-looking configuration, and an unaffected ordinary Git command.
- `tests/test_shell_executor.py` contains an execution-level regression that uses a temporary Git repository or equivalent fixture and proves the payload marker is absent after rejection.
- `SECURITY.md` documents that command-scoped Git configuration overrides are rejected categorically.
- Repository quality commands and `cflx openspec validate reject-git-config-overrides --archive-gate` succeed.
- Release/advisory preparation identifies a concrete patched version greater than `1.1.1`; publishing remains a human-controlled release action.

## Out of Scope

- Building a complete sandbox for every allowed executable.
- Supporting an allowlist of selected `git -c` keys.
- Changing shell parsing, redirection containment, or process environment behavior unrelated to this Git argument bypass.
- Publishing the package or private advisory as part of automated implementation.
