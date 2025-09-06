# コードベース構造

## ディレクトリ構成
```
mcp-shell-server/
├── src/mcp_shell_server/     # メインソースコード
├── tests/                    # テストファイル
├── .github/                  # GitHub Actions設定
├── .serena/                  # Serena MCP設定
└── [設定ファイル群]
```

## メインモジュール構成
```
src/mcp_shell_server/
├── __init__.py              # パッケージエントリポイント
├── version.py               # バージョン情報
├── server.py               # MCPサーバーメイン実装
├── shell_executor.py       # シェルコマンド実行エンジン
├── command_validator.py    # コマンド検証ロジック
├── command_preprocessor.py # コマンド前処理
├── process_manager.py      # プロセス管理
├── io_redirection_handler.py # I/Oリダイレクト処理
└── directory_manager.py    # ディレクトリ管理
```

## テスト構成
- **19個のテストファイル** で包括的テストカバレッジ
- 機能別テスト（validator, executor, server等）
- エラーケース・エッジケース専用テスト  
- macOS固有テスト
- パイプライン・リダイレクション専用テスト

## 主要クラス・モジュール
- **ExecuteToolHandler**: MCPツール実行ハンドラー
- **CommandValidator**: セキュリティ検証
- **ShellExecutor**: コマンド実行エンジン
- **ProcessManager**: プロセス生成・管理
- **IORedirectionHandler**: I/Oリダイレクト
- **DirectoryManager**: ディレクトリ検証