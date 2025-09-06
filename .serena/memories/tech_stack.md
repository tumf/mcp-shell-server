# 技術スタック

## 言語・ランタイム
- **Python**: 3.11以上（メイン言語）
- **非同期処理**: asyncio

## 依存関係
- **mcp**: >=1.1.2（Model Context Protocol実装）
- **asyncio**: >=3.4.3（非同期処理）

## 開発ツール
- **テスト**: pytest, pytest-asyncio, pytest-cov, pytest-mock
- **コードフォーマット**: black（88文字行長）
- **コードソート**: isort（blackプロファイル）
- **リンター**: ruff
- **型チェック**: mypy
- **プレコミット**: pre-commit

## ビルド・パッケージ
- **ビルドシステム**: hatchling
- **パッケージマネージャー**: uv (pyproject.toml)
- **バージョン管理**: hatch.version

## 配布・統合
- **Smithery**: MCP サーバー配布プラットフォーム統合
- **Claude Desktop**: 直接統合対応