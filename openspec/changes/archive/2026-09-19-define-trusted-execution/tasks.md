## Implementation Tasks

- [x] Add repository tests that bind README and SECURITY.md to the trusted-execution contract and reject an unqualified complete-sandbox claim. (verification: integration - `tests/test_trusted_execution_contract.py` reads the shipped `README.md` and `SECURITY.md` from disk and asserts the required boundary statements plus the absence of the unqualified "secure shell command execution server" claim; run `uv run pytest -q`; verification-id: trusted-execution-contract)
- [x] Rewrite the README introduction and security guidance to define direct command-name admission, retained non-exhaustive hardening, and concrete external isolation boundaries. (verification: integration - `TestReadmeContract` asserts the introduction names the trusted-execution boundary, the `## Trusted execution contract` section scopes allowlists to directly launched names, the hardening rules survive as non-exhaustive defense in depth, and all six external-isolation boundaries are present; run `uv run pytest -q`; verification-id: trusted-execution-contract)
- [x] Align SECURITY.md guarantees, non-guarantees, deployment guidance, and vulnerability-reporting scope with the same threat model. (verification: integration - `TestSecurityPolicyContract` asserts separated Guarantees/Non-guarantees sections, the authority-delegation definition, the trusted-client-versus-trusted-content distinction, retained non-exhaustive hardening, deployment isolation boundaries, and the reporting scope that still covers enforced boundaries; run `uv run pytest -q`; verification-id: trusted-execution-contract)
- [x] Emit one operator warning through the existing logger during server startup and verify that MCP stdout framing is unchanged. (verification: integration - `TestStartupWarning` drives the real `main()` with `stdio_server` and `app.run` mocked and asserts exactly one `WARNING` record carrying `TRUSTED_EXECUTION_WARNING`, that stdout stays empty, and that no log handler targets stdout; run `uv run pytest -q`; verification-id: runtime-trust-warning)
- [x] Clarify the MCP tool description without changing tool names, schemas, environment variables, or execution behavior. (verification: unit - `TestToolDescriptionContract` builds `ExecuteToolHandler().get_tool_description()` in memory and asserts the description names the execution boundary while the tool name, input schema properties, and required fields are unchanged; run `uv run pytest -q`; verification-id: trusted-execution-contract)
- [x] Record the startup warning and clarified trusted-execution contract under Unreleased in CHANGELOG.md. (verification: integration - `TestChangelogContract` parses the Unreleased section of the shipped `CHANGELOG.md` and asserts it records the startup warning and the trusted-execution contract; run `uv run pytest -q`; verification-id: trusted-execution-contract)
- [x] Run the complete repository quality gates and retain every existing command-specific security regression. (verification: integration - the full suite plus formatting, lint, and type checks run against the real repository; run `uv run pytest -q && uv run black --check . && uv run isort --check . && uv run ruff check . && uv run mypy src/mcp_shell_server tests`; verification-id: compatibility-preserved)

## Notes

- Implementation artifacts: `tests/test_trusted_execution_contract.py` (new, 22 tests), `README.md` (new `## Trusted execution contract` section placed before the configuration examples, revised introduction and `## Security` preamble), `SECURITY.md` (reporting scope, trusted-execution contract, guarantees/non-guarantees, defense in depth, deployment guidance), `src/mcp_shell_server/server.py` (`TRUSTED_EXECUTION_WARNING`, `emit_trusted_execution_warning()` called from `main()`, clarified `ExecuteToolHandler.description`), `CHANGELOG.md` (Unreleased).
- Startup-warning wiring is verified through `main()` with `stdio_server` and `app.run` mocked, so the warning is asserted on the real startup path rather than only on the helper.
- evidence: `uv run pytest -q` -> 362 passed, 1 warning (pre-existing asyncio `Event loop is closed` ResourceWarning, unchanged by this change).
- evidence: `uv run black --check .` -> 31 files would be left unchanged; `uv run isort --check .` -> clean; `uv run ruff check .` -> All checks passed.
- evidence: `uv run mypy src/mcp_shell_server tests` -> no errors (one pre-existing informational note at `src/mcp_shell_server/process_manager.py:154`).
- Verification-type alignment: the proposal declares `execution_class: repository-local` with `rerun: uv run pytest -q` for all three verification ids and does not declare unit-only ownership. The new tests read repository documentation files and drive `main()` with mocked MCP transport, so they are repository-local contract/integration-style evidence consistent with the declared verification path; no unit-scope claim is made.
- Backward compatibility: no changes to tool name, request/response schemas, environment variable names, subprocess semantics, or any command-specific validator. All pre-existing security regression tests pass unchanged.

## Final Validation

- `uv run pytest -q`
- `uv run black --check .`
- `uv run isort --check .`
- `uv run ruff check .`
- `uv run mypy src/mcp_shell_server tests`
- `cflx openspec validate define-trusted-execution --archive-gate`
- Inspect server startup stderr and verify no warning text appears on MCP stdout.
