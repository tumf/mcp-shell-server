---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2
  - src/mcp_shell_server/command_validator.py
  - src/mcp_shell_server/io_redirection_handler.py
  - src/mcp_shell_server/process_manager.py
  - src/mcp_shell_server/shell_executor.py
  - src/mcp_shell_server/server.py
  - README.md
  - SECURITY.md
---

# Fix shell execution security boundary

**Change Type**: implementation

## Premise / Context

- A private GitHub Security Advisory, GHSA-6rrx-pj43-m9p2, reports command allowlist bypass, redirection path escape, pipeline shell injection, environment secret exposure, missing audit logging, and missing default execution limits.
- The repository currently has no canonical `openspec/specs` entries, so this proposal adds a new tracked shell execution security capability.
- Current execution code is concentrated in `command_validator.py`, `io_redirection_handler.py`, `process_manager.py`, `shell_executor.py`, and `server.py`.
- README currently claims commands are executed without shell interpretation, while the code uses `asyncio.create_subprocess_shell()`.

## Inferred Request

- Create an implementation proposal for addressing GHSA-6rrx-pj43-m9p2 in `mcp-shell-server`.
- Include runtime hardening, regression tests, and documentation updates.
- Make the proposal complete enough for Conflux to implement without relying on unstated context.

## Problem / Context

The current command allowlist is treated as the primary security boundary, but it only validates `argv[0]`. Allowed binaries can invoke non-allowed programs through their own exec-capable arguments. Redirection paths are resolved with `os.path.join()` without containment checks, allowing reads and writes outside the requested working directory. Pipeline segment names are passed to a shell, and `ALLOW_PATTERNS` uses prefix matching, enabling metacharacter injection when patterns are configured. Child processes inherit all parent environment variables, which can expose server secrets to command output. Commands also lack a server-side default timeout, output size cap, and structured audit logging.

## Proposed Solution

Redefine command execution as an explicit runtime security boundary:

- Execute commands with argv-based subprocess APIs instead of shell string execution for normal single-command and pipeline paths.
- Preserve argv for each pipeline segment and validate every segment before execution.
- Harden command and argument policy so `ALLOW_PATTERNS` uses full matching and known exec-capable command vectors are rejected unless a future explicit argument policy allows them.
- Resolve redirection paths with strict containment under the validated working directory before opening files.
- Run child processes with a minimal, allowlisted environment instead of inheriting `os.environ` wholesale.
- Apply server-side default timeout, maximum timeout, and output byte caps even when the client omits timeout.
- Emit structured audit logs for allowed, rejected, timed-out, and output-capped invocations while redacting secret-like values.
- Update README, SECURITY, and CHANGELOG so security claims match implementation behavior.

## Acceptance Criteria

- Command execution no longer uses `asyncio.create_subprocess_shell()` on normal single-command or pipeline paths.
- The command validator rejects known exec-capable bypass vectors such as `find -exec`, shell/interpreter commands, `awk system()`, `tar --checkpoint-action=exec`, `xargs`, and `env` under default policy.
- `ALLOW_PATTERNS=ls` permits only full matches and does not allow `lsof`, whitespace-bearing shell strings, or metacharacter-bearing command names.
- Input and output redirection targets must be relative paths contained under the validated `directory`; absolute paths, `..` traversal, and symlink escapes are rejected before files are opened.
- Pipeline commands preserve argv and execute normal pipelines such as `echo hello | grep h` while rejecting shell metacharacter injection.
- Child processes do not receive parent secrets such as `SECRET_TOKEN` unless explicitly allowlisted by a documented configuration.
- Every command invocation has a default timeout and output byte cap, and long-running or infinite-output commands terminate safely.
- Structured audit logs are emitted for success, rejection, timeout, output cap, and process error cases without logging raw secrets.
- Documentation reflects the new guarantees and explicitly warns that a command-name allowlist alone is not a complete sandbox.

## Explicit Completion Conditions

This proposal is complete when repository evidence shows all of the following:

- `src/mcp_shell_server/process_manager.py` exposes argv-based process creation and pipeline execution paths that use `asyncio.create_subprocess_exec()` for normal execution.
- `src/mcp_shell_server/shell_executor.py` passes full argv arrays through validation, redirection handling, and pipeline execution without dropping arguments.
- `src/mcp_shell_server/io_redirection_handler.py` rejects escaping redirection targets using realpath/commonpath containment before any read/truncate/open side effect.
- `src/mcp_shell_server/command_validator.py` uses fullmatch semantics for patterns and rejects default dangerous exec-capable vectors.
- `src/mcp_shell_server/server.py` applies bounded timeout behavior and passes the effective timeout into the executor/process layer.
- Tests under `tests/` fail against the old vulnerable behavior and pass against the hardened implementation.
- `README.md`, `SECURITY.md`, and `CHANGELOG.md` are updated to match the implemented security model.
- `pytest`, `ruff`, and `mypy` or the repository's equivalent configured checks have been run, with any known exceptions documented in the implementation handoff.

## Out of Scope

- Designing a fully general per-command argument policy language beyond the default deny rules needed to close the advisory.
- Providing OS-level sandboxing, containers, seccomp, chroot, or mandatory access controls.
- Publishing or reopening the private GitHub Security Advisory.
- Requesting a CVE.
