---
change_type: implementation
priority: high
verifications:
  - id: send-email-selector-regression
    requirement: Known send-email selectors reject before process creation while SMTP/data neighbors remain supported
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: tests/test_command_validator.py
    evidence: uv run pytest tests/test_command_validator.py tests/test_shell_executor.py -q
    rerun: uv run pytest tests/test_command_validator.py tests/test_shell_executor.py -q
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
---
# Reject Git send-email external-program selectors

**Change Type**: implementation

## Context and observable result

The earlier Git fix covers grep/rebase/filter-branch/bisect, but the reported send-email SMTP program selector is still accepted. A full installed executor invoked harmless local helpers via smtp-server and sendmail-cmd in an isolated, network-denied fixture; the directly invoked helper was not allowlisted and was rejected. Git 2.53.0 source also exposes to-cmd, cc-cmd, and header-cmd. This violates the explicit known Git external-program rejection contract. After this change all five selectors are recognized before process creation, while ordinary SMTP host use and selector-looking data remain allowed.

## Fixed design and change boundary

Follow design.md exactly. Add a dedicated finite three-pass Getopt::Long-shaped recognizer for exact send-email after the existing global-prefix resolver. Do not reuse grep/rebase grammar: send-email is Perl, case-insensitive, supports single-dash/plus long names, and parses residual argv in three passes. No generic shell containment or dynamic runtime inspection.

Production change is confined to src/mcp_shell_server/command_validator.py (one sibling helper module is allowed only if needed to avoid growing that file); tests to tests/test_command_validator.py and tests/test_shell_executor.py. Update README.md, SECURITY.md, CHANGELOG.md and the new command-policy requirement. Existing tar/PATH/Git rules and MCP APIs must remain unchanged. No dependencies, configuration, workflows or versions change.

Reject all reachable sendmail-cmd/to-cmd/cc-cmd/header-cmd selections, including empty/missing values and dry-run/overridden selections. Reject smtp-server only for missing/empty or program-like values: beginning slash/backslash, or ASCII drive-letter colon. This is a documented conservative cross-platform union, not native Windows runtime proof. Hostnames/IPs and relative strings remain allowed. Ambiguous prefixes including a prohibited selector may be conservatively rejected; do not claim all such strings execute in Git.

## Preserved contracts and alternatives

Keep status, ordinary grep/rebase, help/alias listing, SMTP host dry-run, longer exact smtp-server-port/option, consumed option-looking subject/identity values, and data after a genuine delimiter. Existing independent broad Git checks can still reject these inputs for their own reasons. Do not categorically reject send-email: that would unnecessarily remove SMTP/help support. Do not scan substrings across argv: it both breaks data values and misses upstream spellings. Do not try to classify arbitrary command text as harmless or require it to be executable on this host.

## Acceptance Criteria

- Implement the fixed option tables, recognition passes, path classification, and dispatch described in design.md. Tests first: the four basic smtp-server/sendmail-cmd forms must fail under base before the code change.
- Cover full/equal/separate/prefix/case/single-dash/plus forms, permutation, early-pass residual conflicts, required/optional/numeric consumption, genuine and consumed delimiters, exact neighbor precedence, and negated flags.
- Validator and executor tests assert the specific Git default security-policy error; executor/pipeline rejection asserts process methods were not awaited and no helper marker/output exists. Cover exact/pattern/absolute-name admission, global prefix values, both pipeline positions.
- All declared focus tests, full pytest suite, lint/typecheck and diff checks pass; docs and canonical spec match the implemented finite policy. Public artifact acceptance and independent review remain parent-owned release gates, not substituted by test mocks.

## Explicit Completion Conditions

Executable tests, not stored reports, prove the new rejection and permitted neighbors. A no-op or categorical send-email ban must fail them. Preserve every other command family and existing Git true rejection. No actual email or network delivery in repository tests; use prelaunch boundary spies. Publish no release or advisory from this change.

## Final Validation

Run focus gate once, uv run pytest -q, uv run make lint typecheck, git diff --check, and cflx openspec validate fix-git-send-email-selectors --archive-gate. The tracked hook is not configured in this checkout, so explicit checks remain required. Archive must promote the added requirement without overwriting existing command-policy requirements.

## Out of Scope / Future Work

Parent owns final Fable review, clean wheel and public PyPI acceptance, release and advisory publication. Generic Git configs/hooks/aliases/autocorrect, difftool/submodule child execution, future Git grammar, and Windows runtime reproduction are not implemented here. Document both configuration-driven and argv-driven residual helpers without revoking any concrete rejection promise.
