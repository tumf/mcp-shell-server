---
change_type: implementation
priority: high
dependencies: []
verifications:
  - id: finite-policy-regression
    requirement: Known wrapper and find execution forms are rejected without weakening unrelated controls or claiming sandboxing
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: tests/test_command_validator.py
    evidence: uv run pytest tests/test_command_validator.py tests/test_trusted_execution_contract.py tests/test_shell_executor.py
    rerun: uv run pytest tests/test_command_validator.py tests/test_trusted_execution_contract.py tests/test_shell_executor.py
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
---
# Align known execution policy and finite trust contract

**Change Type**: implementation

## Problem / Context
Known execution wrappers and JS runtimes setarch, strace, valgrind, deno and bun bypass the current dangerous-name set even when the canonical command policy promises wrapper/interpreter rejection. find interactive execution primaries -ok/-okdir pass the command validator; their required standalone semicolon already fails executor preprocessing, so this is not an end-to-end exploit claim. Canonical command-policy also makes a universal wrapper rejection claim inconsistent with the selected trusted-execution product. Fix the concrete omissions and explicitly reconcile the scope, rather than waiving them retroactively.

## Proposed Solution
Add exactly setarch,strace,valgrind,deno,bun to existing DANGEROUS_COMMANDS. Existing basename normalization and pre-allowlist rejection must apply unchanged to exact allowlists, pattern allowlists, absolute paths and pipeline stages. This categorical block includes version/attach-only forms; document the compatibility effect. No allowlist override and no new policy mode.

Extend find's exact execution primary set from -exec/-execdir to -exec/-execdir/-ok/-okdir for find/gfind/bfind with one family-specific error. Preserve the existing shared semicolon preprocessing rejection; tests distinguish validator policy rejection from preprocessor rejection. Do not parse find globally or change benign search/output rules.

Explicit product/specification decision: preserve trusted argv execution (not sandbox), reject the existing finite name/argument rules and the newly verified ones, and state that the policy does NOT recognize every program capable of launching helpers. General make recipe execution and dd/tee program-owned file writes remain delegated authority when those programs are allowlisted, not newly blocked capabilities. This is a visible correction of the overly broad canonical promise, not an assertion that the omissions were never defects. README, SECURITY and canonical MUST agree. Preserve all existing concrete git/sort/tar/awk rejection obligations and other specification scenarios; Git expansion and tar grammar are separate changes.

## Acceptance Criteria
- For each new dangerous name, parameterize bare/absolute name and exact/pattern allowlist tests, plus a pipeline later-stage rejection. Verify error before subprocess creation and no marker/output creation.
- find aliases reject each execution primary by validator policy; ordinary find name/print remains allowed. Full executor rejection retains original preprocessing; do not mistake semicolon rejection as find-policy coverage.
- Existing dangerous tools remain blocked, including when explicitly allowed; no bypass flag.
- Tests explicitly establish the honest scope: ordinary make command validation and dd/tee program-owned path operands remain allowed, without unsafe host writes. Canonical/readme/SECURITY explain delegated behavior and OS/container isolation for hostile workloads.
- Full existing suite/lint/typecheck and archive gate pass; no weakening of existing git/sort/tar/awk rules.

## Change Boundary
DANGEROUS_COMMANDS and exact find primary check in command_validator.py, focused validator/executor/contract tests, README, SECURITY, CHANGELOG, canonical command-policy and selected trusted-execution wording. No Git algorithm, tar parser, PATH, dependency, network preflight or sandbox implementation. Multiple parallel proposals may touch the same policy/docs; merge must preserve their independently accepted behavior.

## Explicit Completion Conditions
Known name/primary gaps closed with process-free assertions, finite product contract made explicit, concrete previously guaranteed rejects preserved, full checks pass. Parent independently verifies Linux wrapper and published artifact behavior, release and coordinated disclosures.

## Out of Scope
Generic make sandbox, dd/tee confinement, all future wrappers, fixed-operation APIs, new modes or OS isolation implementation. No blanket CVSS or E2E claim for find.

## Final Validation
uv run pytest tests/test_command_validator.py tests/test_trusted_execution_contract.py tests/test_shell_executor.py; full suite, make lint, make typecheck; cflx openspec validate align-known-execution-policy --archive-gate.
