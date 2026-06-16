# Design: Shell execution security boundary

## Overview

The current implementation mixes argv-style user input with shell-string execution. This creates a mismatch between the documented model and the runtime model. The hardened design should make argv the internal representation from request parsing through process creation and should treat shell features as unsupported unless a future proposal explicitly adds a safe policy for them.

## Current Architecture

- `server.py` receives MCP `shell_execute` arguments and invokes `ShellExecutor.execute()`.
- `shell_executor.py` preprocesses command arrays, handles pipeline/redirection branching, and delegates to `ProcessManager`.
- `command_validator.py` reads `ALLOW_COMMANDS`, `ALLOWED_COMMANDS`, and `ALLOW_PATTERNS` from environment variables.
- `io_redirection_handler.py` parses `<`, `>`, and `>>` tokens and opens file handles.
- `process_manager.py` creates subprocesses, executes them with optional timeout, and cleans them up.

## Target Architecture

### argv-first execution

`ShellExecutor` should preserve commands as `list[str]` and pipelines as `list[list[str]]`. `ProcessManager` should expose argv-based methods for single-command and pipeline execution. Normal execution should call `asyncio.create_subprocess_exec(*argv, ...)`.

This avoids shell parsing of user-controlled strings and makes validation match execution.

### Pipeline execution

Pipeline support should not rely on shell syntax. Each pipeline segment should be a validated argv list. The process manager can either:

1. execute segments sequentially by feeding captured stdout to the next process, preserving current behavior, or
2. wire subprocess pipes concurrently.

The minimal implementation may keep the existing sequential behavior if tests and documentation reflect it. The critical requirement is that argv arguments are preserved and segment names are not shell-interpreted.

### Command policy

`ALLOW_COMMANDS` remains a command-name allowlist for backward compatibility, but it is not sufficient as a sandbox. The validator should add default hardening for known vectors reported by GHSA-6rrx-pj43-m9p2. A future proposal can add a richer per-command policy language if needed.

`ALLOW_PATTERNS` should be treated as a command-name pattern, not an arbitrary shell string pattern. Fullmatch semantics and metacharacter rejection keep pattern behavior compatible with command identity validation.

### Redirection containment

Redirection target resolution should happen before any file open side effect:

1. require a non-empty relative path,
2. reject absolute paths,
3. reject `..` path segments,
4. resolve `base = realpath(directory)` and `target = realpath(join(base, user_path))`,
5. require `commonpath([base, target]) == base`.

This protects against absolute path override, traversal, and symlink escape.

### Environment isolation

The process manager should construct a minimal child environment. A reasonable default is a fixed safe `PATH` plus explicitly allowed variables. Parent process secrets should not be forwarded by default. Redaction logic for audit logging should treat secret-like names and values defensively.

### Execution limits

Timeout and output cap enforcement should live close to process execution so both direct and pipeline paths share the behavior. `server.py` should compute and validate client-facing timeout bounds, while `ProcessManager` should enforce the effective timeout and output byte cap.

For output caps, streaming reads are preferable to unbounded `communicate()`. If a minimal implementation initially uses bounded reads around pipes, it must still prove that excessive output does not accumulate unbounded memory.

### Audit logging

Audit logging should be structured and outcome-oriented. It should not log raw stdout/stderr or unredacted secrets. Rejection audit should occur before process creation when validation fails. Runtime outcome audit should occur after process completion, timeout, cap, or error.

## Trade-offs

- Default-denying exec-capable vectors may reject some previously allowed workflows. This is acceptable for a security advisory fix and should be documented as a breaking hardening behavior if necessary.
- A complete argument-policy language would provide more flexibility, but it is larger than needed to close the advisory and is deferred to future work.
- Sequential pipeline execution is less shell-like than concurrent OS pipes, but it can preserve existing behavior while removing shell injection risk.

## Migration Notes

Users who currently rely on `find -exec`, interpreters, `env`, `xargs`, or other exec-capable commands should be told these are no longer safe under the default policy. Documentation should recommend purpose-built, constrained commands or a future explicit policy mechanism rather than broad allowlisting.
