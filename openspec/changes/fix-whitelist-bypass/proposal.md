---
change_type: implementation
priority: high
dependencies: []
references:
  - "src/mcp_shell_server/command_validator.py:86-106"
  - "openspec/specs/command-policy/spec.md:23-54"
  - "tests/test_command_validator.py:102-155"
---

# fix-whitelist-bypass

**Change Type**: implementation

## Problem / Context

アドバイザリ GHSA-6rrx-pj43-m9p2 の Issue #1「Whitelist validates only `argv[0]`」が未修正です。`ALLOW_COMMANDS=git` のような一般的な許可設定で、`git -c alias.pwn=!sh -c "touch marker"` のような exec-capable 引数により任意コードが実行可能です。既存の `DANGEROUS_COMMANDS` 拒否リストは `find`/`awk`/`tar` などを対象としていますが、汎用的な argv ポリシー（許可されたバイナリの危険引数全般の拒否）は未実装です。

## Proposed Solution

- `command_validator.py` の `_validate_default_argument_policy` を拡張し、許可されたバイナリでも exec-capable な引数（`git -c alias.*=!...`、`xargs sh -c` 等）をデフォルトで拒否する。
- 拒否対象をドキュメント化し、テストで PoC をカバーする。
- 既存 `DANGEROUS_COMMANDS` ロジックと整合させつつ、汎用的な argv 検証を追加する。

## Acceptance Criteria

- `ALLOW_COMMANDS=git` 設定時に `git -c alias.pwn=!sh -c "touch marker"` が拒否される。
- 拒否はプロセス生成前に発生し、audit log に `rejected` が残る。
- 既存の `find`/`awk`/`tar`/`env` 拒否テストが引き続きパスする。
- 新規 PoC テストが追加され、CI で実行される。

## Explicit Completion Conditions

- `src/mcp_shell_server/command_validator.py` の `_validate_default_argument_policy` が git 等を拒否するコードを含む。
- `tests/test_command_validator.py` に `git`/`xargs` などの PoC テストが追加され、`pytest tests/test_command_validator.py` がパスする。
- `cflx openspec validate fix-whitelist-bypass --strict --evidence warn` がエラーなく完了する。

## Out of Scope

- ユーザー定義ポリシーの完全実装（将来の拡張）。
- 外部バイナリの静的解析（`git` の全サブコマンド走査等）。
- 既存 `DANGEROUS_COMMANDS` 以外の新しい危険コマンドの包括的リスト作成。
