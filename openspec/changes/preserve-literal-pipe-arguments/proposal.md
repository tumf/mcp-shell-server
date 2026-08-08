---
change_type: implementation
priority: high
dependencies: []
references:
  - https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-q8pm-q3r2-q7cg
  - https://github.com/tumf/mcp-shell-server/security/advisories/GHSA-7wg7-jj87-qp4c
verifications:
  - id: literal-pipe-argument-security
    requirement: Literal pipe characters inside argv elements remain data while discrete pipe tokens retain pipeline behavior
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: tests/test_shell_executor_pipeline.py
    evidence: Regression tests prove argv preservation, explicit pipeline compatibility, policy rejection, and absence of subprocess or file side effects
    rerun: uv run pytest tests/test_shell_executor_pipeline.py tests/test_command_validator.py && uv run make all
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
---

# Preserve literal pipe characters in argv arguments

Change Type: implementation

## Problem / Context

`CommandPreProcessor.preprocess_command()` currently splits every argv element containing `|` and inserts a synthetic pipeline boundary before command-specific validation. This corrupts legitimate argument data such as regular expressions, URLs, and JSON. It can also reinterpret following argv elements as independently executed allowlisted pipeline stages and remove pipe characters before `awk` or similar argument policies inspect them.

GitHub Security Advisories GHSA-q8pm-q3r2-q7cg and GHSA-7wg7-jj87-qp4c report the same root cause. The defect exists in `main` and release `v1.1.7`.

## Proposed Solution

Stop splitting pipe characters embedded inside argv elements. Recognize pipeline syntax only when the client supplies `|` as its own argv element. Preserve the existing explicit-pipeline execution path and command-policy validation. Add focused regression tests covering literal data, unintended pipeline construction, command-specific policy enforcement, and side-effect suppression.

After implementation verification, prepare the repository metadata for a patched release. Publishing the package and Security Advisories remains an explicit owner-controlled external action.

## Acceptance Criteria

- Every argv element other than the discrete token `|` reaches validation and execution unchanged, including leading, trailing, and embedded pipe characters.
- `['grep', '-E', 'error|warning', 'file.txt']` remains one command with the regular expression intact.
- `['echo', 'text|', 'id']` does not create a second pipeline stage or execute `id` independently.
- Command-specific policies inspect the original argument content and reject prohibited embedded-pipe payloads.
- A pipeline expressed with a discrete `|` token continues to validate and execute normally.
- Rejected payloads create no subprocess or file side effects.
- The changelog identifies `v1.1.7` and earlier as affected and instructs users to upgrade to the patched release once published.

## Explicit Completion Conditions

- `src/mcp_shell_server/command_preprocessor.py` no longer converts pipe characters inside argv values into syntax.
- Regression tests fail against `v1.1.7` behavior and pass after the fix.
- Tests cover literal regex data, trailing-pipe smuggling, the reported `awk` policy path, explicit pipelines, and no-side-effect rejection.
- `uv run pytest tests/test_shell_executor_pipeline.py tests/test_command_validator.py` passes.
- `uv run make all` passes.
- Release-facing documentation records the security fix without publishing any external artifact.

## Out of Scope

- Removing explicit pipeline support.
- Redesigning the command allowlist or all command-specific policies.
- Publishing a package, GitHub Release, Security Advisory, issue comment, or other external communication.
- Assigning final CVSS severity or deciding which duplicate Advisory remains primary.
- Fixing unrelated dependency or security findings.
