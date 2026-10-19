---
change_type: implementation
priority: high
dependencies: []
verifications:
  - id: child-path-regression
    requirement: Real process creation uses the configured safe PATH without ambient inheritance unless explicitly delegated
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: tests/test_process_manager.py
    evidence: uv run pytest tests/test_process_manager.py tests/test_shell_executor.py
    rerun: uv run pytest tests/test_process_manager.py tests/test_shell_executor.py
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
---
# Fix safe child PATH

**Change Type**: implementation

## Problem / Context
The runtime module-level environment builder inherits the parent PATH and ignores MCP_SHELL_SAFE_PATH. A second, unused instance builder uses SAFE_PATH but accepts unfiltered env overrides. Tests accidentally bless both implementations. Released README promises SAFE_PATH; POSIX executable lookup uses the environment passed to create_subprocess_exec.

## Proposed Solution
Keep one authoritative module-level builder. Initialize PATH from a nonblank MCP_SHELL_SAFE_PATH, otherwise DEFAULT_SAFE_PATH on POSIX. Preserve a nonblank configured value byte-for-byte. On Windows use a nonblank configured SAFE_PATH; otherwise preserve parent PATH and use os.defpath only when parent PATH is absent. This child value does not control Windows native bare-name executable search and MUST NOT be advertised as safe executable lookup. Preserve existing Windows launch keys. Do not introduce a Windows resolver or normalize Windows environment key semantics in this change.

Preserve explicit delegation: an exact PATH entry in MCP_SHELL_CHILD_ENV_ALLOWLIST permits parent PATH and per-call envs PATH in that order; per-call wins. Explicitly delegated PATH values, including empty strings, are passed unchanged. An allowlisted but missing value falls back to configured/default PATH. Nonallowlisted envs PATH is ignored. This is operator opt-in, not an escape through untrusted per-call config.

Replace the duplicate instance method with a thin delegation to the module-level function, preserving the callable Python method. Remove the now-unused MCP_SHELL_ENV_ALLOWLIST constant and do not revive that obsolete setting. Keep existing allowed-key validation/redaction, secret filtering, pipeline environment handling, and callable signatures unchanged; instance method semantics become identical to the module function. Do not add LANG/LC_ALL implicitly.

## Acceptance Criteria
- POSIX real ShellExecutor normal and every pipeline stage (not only the final stage) use only configured/default PATH, not an earlier fake executable in parent PATH.
- A command absent from configured PATH must fail without falling back to parent PATH.
- Empty/whitespace SAFE_PATH uses default; nonempty directory names containing spaces retain bytes.
- Explicit CHILD_ENV_ALLOWLIST=PATH permits parent/per-call PATH delegation; omission keeps protection. Neither per-call configuration variable nor the old unused allowlist changes server policy.
- Instance builder and process creation share the same filtering and PATH behavior.
- Unrelated variables and synthetic secrets remain excluded; safe neighboring commands work.
- README, process-environment spec and changelog describe precedence and compatibility impact: non-system tools require MCP_SHELL_SAFE_PATH or explicit PATH delegation.

## Change Boundary
Only process_manager.py, relevant existing tests, README, CHANGELOG and process-environment spec delta/canonical are in scope. No find/tar policy, transport, dependency, release-version or public advisory changes.

## Explicit Completion Conditions
Regression tests exercise actual create_process and real executor normal/pipeline paths, not only helper output. A harmless fixture in parent PATH remains unexecuted without delegation and executes only in explicit opt-in tests. Full tests, lint and typecheck remain green. No registry publication or external checks are claimed by local acceptance.

## Out of Scope
Windows native executable search isolation and existing Windows import/platform limitations; rejecting operator-configured relative PATH components; PATH filesystem trust/TOCTOU; generic sandboxing; changing command allowlist semantics. No new dependencies.

## Final Validation
Run focused regression, full suite, make lint and make typecheck, and cflx openspec validate fix-safe-child-path --archive-gate. Release artifact and public PyPI acceptance remain parent release responsibilities, not Conflux checkbox tasks.
