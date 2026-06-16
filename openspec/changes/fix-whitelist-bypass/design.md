# Design: fix-whitelist-bypass

## Architecture Decision

### Pattern: git alias exec detection via `-c alias.*=!`

**Chosen**: `_validate_default_argument_policy` に git 専用の引数チェックを追加する。git alias の外部コマンド実行機構は `git -c alias.<name>=!<cmd> <name>` の形式に依存するため、`-c` 引数に続く値が以下の両条件を満たす場合に拒否する：

1. 値が `alias.` を含む
2. 値が `=!` を後続に含む

このパターンは `git -c alias.pwn=!sh -c "id" pwn` のような典型攻撃を捕まえつつ、通常の `git -c user.name=Foo` のような設定は許可する。

**Rejected alternatives**:

| Alternative | Why rejected |
|-------------|--------------|
| git を `DANGEROUS_COMMANDS` に追加 | git は広く使われるユーティリティであり、exec 以外の用途（log, diff, status 等）を全て禁止するのは非現実的 |
| `-c` 値が `!` を含む全てを拒否 | `git -c core.commentChar=!` のような非 exec 設定も誤拒否する |
| git サブコマンドの allowlist（`git log`, `git status` のみ許可） | 実装コストが高く、サブコマンドの列挙漏れリスクがある |

### Pattern: xargs は既存カバレッジ

`xargs` は `command_validator.py` の `DANGEROUS_COMMANDS` set に含まれており、既に完全拒否されている。本提案では spec delta にドキュメントとしての xargs シナリオは含めず、実装タスクも追加しない。

## Data Flow

```
client → server.py → shell_executor.py → command_validator.py
                                              │
                                     _validate_default_argument_policy()
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                         cmd in             cmd ==         cmd ==
                     DANGEROUS_COMMANDS?     "find"?        "git"?
                              │               │               │
                          REJECT          -execあり?    -c alias.*=! ?
                                              │               │
                                          REJECT           REJECT
```

既存の `DANGEROUS_COMMANDS` → `find -exec` → `awk system()` → `tar --checkpoint-action=exec` のチェーンに、`git -c alias.*=!` チェックを追加する。各チェックは互いに独立しており、早期リターンで最初にマッチした拒否理由を返す。

## Failure Handling

- 拒否時は `ValueError("Command rejected by default security policy: git alias exec")` を raise する。
- `shell_executor.py` の既存の reject パスが audit log（`result_type: rejected`）を生成し、プロセス生成前にクライアントへエラーが返る。
- 正規表現ではなく文字列包含チェックを使うため、パターンマッチに起因する例外は発生しない。
