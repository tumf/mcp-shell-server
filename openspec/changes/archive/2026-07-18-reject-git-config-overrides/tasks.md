## Implementation Tasks

- [x] Replace Git configuration-key denylisting with categorical rejection of separated and attached `git -c` forms in `src/mcp_shell_server/command_validator.py`; preserve existing external-program option and `ext::` transport checks. (verification: unit - `tests/test_command_validator.py` rejects all command-scoped configuration while allowing `git status`)
- [x] Add validator regressions for `core.fsmonitor`, `diff.external`, benign-looking `user.name`, mixed case where applicable, missing values, and both `-c` token forms. (verification: unit - `pytest tests/test_command_validator.py` exercises each case through `CommandValidator.validate_command`)
- [x] Add an executor-level regression using an isolated temporary Git repository that submits at least one advisory payload and asserts rejection plus absence of its marker file. (verification: integration - `pytest tests/test_shell_executor.py` must fail if a subprocess executes the injected command)
- [x] Update `SECURITY.md` to state that all Git command-scoped configuration overrides are rejected and remove wording that implies a maintainable executable-key denylist. (verification: manual - compared `SECURITY.md` with `src/mcp_shell_server/command_validator.py`; both categorically reject `git -c` forms)
- [x] Reconcile the implementation with any pre-existing uncommitted argument-hardening work without weakening its unrelated protections. (verification: unit - `tests/test_command_validator.py` preserves dangerous-command, Git transport, and ordinary-command coverage)
- [x] Prepare version and advisory metadata for a patched release greater than `1.1.1`, keeping `<=1.1.1` in the vulnerable range and naming the concrete patched version. (verification: manual - `src/mcp_shell_server/version.py` and `CHANGELOG.md` identify `1.1.2` as patched and `<=1.1.1` as affected; private advisory publication remains repository-owner controlled)
- [x] Run all repository-provided quality commands and resolve failures attributable to this change. (verification: integration - `pytest`, `ruff check .`, `black --check .`, and `mypy src` exit successfully)

## Future Work

- Repository owner publishes the patched package release.
- Repository owner updates and publishes `GHSA-56qh-7rgp-wfgr` only after confirming the patched artifact is available.

## Final Validation

Archive validation is the authoritative final OpenSpec gate.
Expected archive gate: `cflx openspec validate reject-git-config-overrides --archive-gate`

## Acceptance #1 Failure Follow-up
- [x] `CHANGELOG.md:13` の項目が `+-` で始まるためリリースメタデータが不正。通常の `-` 箇条書きへ修正すること。品質ゲート `make all`、archive gate、全タスクの `[x]`、clean worktree、有効 commit hook なしは確認済み。
- [x] `README.md:116,213-218` が Git alias のみを拒否する旧キー固有モデルを説明しており、全 `git -c` 拒否を明示する `SECURITY.md:25` と不一致。選択した設定だけが危険という含意を除去すること。
- [x] `openspec/changes/reject-git-config-overrides/tasks.md:8` は完了済みだが、実際の `GHSA-56qh-7rgp-wfgr` は `patched_versions` が空で、pip package 名も `tumf/mcp-shell-server` のまま。`proposal.md:44,53` の advisory metadata 完了条件を満たすよう、patched version `1.1.2` と正しい package 名 `mcp-shell-server` を記録すること。
- [x] `src/mcp_shell_server/command_validator.py:134` が全引数の `-c*` を拒否するため、設定上書きではない正規オプション `git commit -c HEAD --dry-run` まで拒否する。Git のグローバルオプション領域だけを判定し、サブコマンド固有の `-c` を許可するテストを追加すること。
- [x] `src/mcp_shell_server/command_validator.py:138-143` は `git clone -u <upload-pack>` を許可する。`-u` は `--upload-pack` の短縮形で外部プログラム指定に該当し、`specs/command-policy/spec.md:31-35` の継続拒否要件を満たさない。サブコマンドを考慮して拒否し、回帰テストを追加すること。(verification: unit - `uv run pytest tests/test_command_validator.py` rejects `git clone -u sh repo`)
