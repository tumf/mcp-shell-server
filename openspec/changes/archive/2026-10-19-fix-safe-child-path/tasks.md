## Implementation Tasks

- [x] Use configured/default PATH in the authoritative environment builder and replace duplicate instance logic with delegation while preserving exact-key allowlist opt-in and secret filtering (verification: integration - tests/test_process_manager.py; verification-id: child-path-regression)
- [x] Replace test_create_process_uses_minimal_child_environment, test_child_environment_does_not_inherit_secrets, and test_child_environment_allows_documented_allowlist expectations using the module builder and MCP_SHELL_CHILD_ENV_ALLOWLIST; add configured/default/blank/missing/delegated PATH tests and real executor normal/pipeline fake-executable negative controls (verification: integration - tests/test_process_manager.py and tests/test_shell_executor.py; verification-id: child-path-regression)
- [x] Update README and changelog, and keep the process-environment ADDED delta promotable by archive without losing existing environment scenarios (canonical spec is promoted by `cflx openspec archive`; manual pre-promotion duplicates or no-ops the archive) (verification: integration - tests/test_process_manager.py; verification-id: child-path-regression)

## Final Validation
Run the declared regression command once, the repository checks, and cflx openspec validate fix-safe-child-path --archive-gate. Preserve existing API and logging boundaries.

## Future Work
Parent owns independent final review, built wheel acceptance, public registry publication, advisory range/credit and disclosure. Windows native executable resolution is not claimed by this POSIX-focused fix.

## Notes
- Archive simulation in a throwaway copy: `cflx openspec archive fix-safe-child-path --yes` promoted the ADDED requirement and kept all three existing process-environment scenarios. Pre-promoting into `openspec/specs/process-environment/spec.md` either duplicated the requirement (ADDED) or failed as a no-op archive (MODIFIED), so canonical promotion is left to archive.
- Negative-control check: with the original `process_manager.py`, 23 of the new/updated tests failed; with the fix all pass.
