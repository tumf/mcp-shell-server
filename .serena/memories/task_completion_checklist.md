# タスク完了時チェックリスト

## 必須実行項目

### 1. コード品質チェック
```bash
make check  # リント + 型チェック
```
- black --check で フォーマット確認
- isort --check で インポート順序確認  
- ruff check で リンター確認
- mypy で型チェック確認

### 2. テスト実行
```bash
make test   # 基本テスト
make coverage  # カバレッジ確認（推奨）
```

### 3. フォーマット適用
```bash
make format  # 自動フォーマット
```

## 推奨実行項目

### 完全チェック
```bash
make all    # format + check + coverage の完全実行
```

## リリース前確認事項

### バージョン確認
- `src/mcp_shell_server/version.py` のバージョン更新
- `CHANGELOG.md` の更新

### セキュリティ確認  
- コマンドホワイトリスト機能が正常動作
- 入力検証が適切に実施
- シェルインジェクション対策が有効

### パフォーマンステスト
- タイムアウト機能テスト
- 大量データ処理テスト
- リソース使用量確認