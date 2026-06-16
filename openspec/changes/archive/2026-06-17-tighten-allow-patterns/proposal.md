---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 4
  - src/mcp_shell_server/command_validator.py
  - tests/test_command_validator.py
---

# Tighten ALLOW_PATTERNS matching

**Change Type**: implementation

## Problem / Context

`ALLOW_PATTERNS` currently uses prefix matching via `re.match()`. A pattern such as `ls` can allow `lsof`, `ls -la /root`, or metacharacter-bearing strings that start with `ls`. This is low severity alone but enables pipeline shell injection when combined with shell execution.

## Proposed Solution

Change allowed pattern semantics to full-command-name matching with `re.fullmatch()` and reject unsafe pattern/input forms containing whitespace or shell metacharacters. Document the semantics so patterns are understood as command identity patterns, not shell command patterns.

## Acceptance Criteria

- `ALLOW_PATTERNS=ls` allows `ls` only, not `lsof`.
- Whitespace-bearing or metacharacter-bearing command strings do not pass pattern validation.
- Pattern behavior is covered by tests.
- README documents fullmatch command-name semantics.

## Explicit Completion Conditions

- `src/mcp_shell_server/command_validator.py` uses fullmatch semantics for `ALLOW_PATTERNS`.
- Tests prove prefix overmatch is no longer possible.
- Documentation no longer suggests patterns can safely describe shell command strings.

## Out of Scope

- A general policy language for argument-level pattern matching.
