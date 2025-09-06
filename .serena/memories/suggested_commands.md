# 開発用コマンド一覧

## テスト
```bash
make test          # 基本テスト実行
pytest             # 直接テスト実行
make coverage      # カバレッジ付きテスト
```

## コード品質チェック
```bash
make check         # リント＋型チェック実行
make lint          # リント確認（エラー時終了）
make typecheck     # mypy型チェック
```

## コードフォーマット
```bash
make format        # 自動フォーマット（black + isort + ruff fix）
make fix          # check + format の組み合わせ
```

## 全体実行
```bash
make all          # format + check + coverage の完全実行
```

## 実行方法
```bash
# 開発版実行
ALLOW_COMMANDS="ls,cat,pwd" uv run mcp-shell-server

# インストール済み実行  
ALLOW_COMMANDS="ls,cat,pwd" uvx mcp-shell-server

# テスト用簡易実行
ALLOWED_COMMANDS="ls,cat,echo" uvx mcp-shell-server
```

## 依存関係管理
```bash
uv sync           # 依存関係同期
uv add package    # パッケージ追加
uv remove package # パッケージ削除
```