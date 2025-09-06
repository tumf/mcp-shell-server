# コードスタイル・規約

## フォーマット
- **black**: 88文字行長、Python 3.11対応
- **isort**: blackプロファイル、88文字行長

## リンター設定（ruff）
- **有効ルール**: 
  - E（pycodestyle エラー）
  - F（pyflakes）  
  - W（pycodestyle 警告）
  - I（isort）
  - C（comprehensions）
  - B（bugbear）
- **無効ルール**:
  - E501（行長制限 - blackで処理）
  - B008（引数デフォルトでの関数呼び出し）
  - C901（複雑さ制限）

## 型ヒント
- mypy による型チェック必須
- src/ および tests/ ディレクトリ対象

## ドキュメント
- 関数・クラスに詳細docstring
- Google/Numpyスタイルのdocstring
- 型情報とRaises情報を含む

## 命名規則
- クラス名: PascalCase（例：ExecuteToolHandler）
- 関数・変数名: snake_case（例：validate_directory）
- 定数: UPPER_SNAKE_CASE（例：ALLOW_COMMANDS）
- プライベート: アンダースコア接頭辞（例：_processes）