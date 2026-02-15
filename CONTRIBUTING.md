# Contributing to Claude Context Manager

Claude Context Managerへのコントリビューションに興味を持っていただき、ありがとうございます！

このドキュメントでは、開発環境のセットアップ、テストの実行、コントリビューションの方法について説明します。

## 目次

- [開発環境のセットアップ](#開発環境のセットアップ)
- [ローカルテストの実行](#ローカルテストの実行)
- [テストの書き方](#テストの書き方)
- [コーディング規約](#コーディング規約)
- [CI/CD要件](#cicd要件)
- [プルリクエストの作成](#プルリクエストの作成)

## 開発環境のセットアップ

### 必要な環境

- **Node.js**: 20.x以上
- **Python**: 3.8以上
- **npm**: Node.jsに付属
- **pip**: Python 3に付属
- **make**: オプション（便利なショートカットコマンド用）

### セットアップ手順

1. **リポジトリをクローン**

```bash
git clone https://github.com/yourusername/claude-context-manager.git
cd claude-context-manager
```

2. **依存関係をインストール**

```bash
# 方法1: Makefileを使用（推奨）
make install

# 方法2: 手動でインストール
npm install
pip install -r requirements-dev.txt
```

3. **TypeScriptをビルド**

```bash
make build
# または
npm run build
```

4. **開発用フックのリンク（オプション）**

開発中のフックをClaude Codeでテストする場合：

```bash
ln -s $(pwd)/src/hooks/user-prompt-submit.py ~/.claude/hooks/
ln -s $(pwd)/src/hooks/post-tool-use.py ~/.claude/hooks/
ln -s $(pwd)/src/hooks/stop.py ~/.claude/hooks/
ln -s $(pwd)/src/hooks/shared ~/.claude/hooks/
```

## ローカルテストの実行

### クイックスタート

```bash
# 全テスト（Python + TypeScript）を実行
make test-all

# Pythonテストのみ
make test-python

# TypeScriptテストのみ
make test-ts

# Watchモード（TypeScript）
make test-watch
```

### npm scriptsを使う場合

```bash
# Pythonテスト
npm run test:python

# TypeScriptテスト
npm test

# TypeScriptテスト（watchモード）
npm run test:watch

# 全テスト
npm run test:all

# カバレッジレポート付き（CI用）
npm run test:ci
```

### 個別のテストを実行

```bash
# 特定のPythonテストファイル
python3 -m pytest tests/test_hooks.py -v

# 特定のテスト関数
python3 -m pytest tests/test_hooks.py::test_session_logger_file_creation_and_loading -v

# 特定のTypeScriptテストファイル
npm test -- path/to/test.test.ts
```

### カバレッジレポート

```bash
# Pythonカバレッジ（HTMLレポート付き）
python3 -m pytest tests/ -v --cov=src/hooks --cov-report=html

# TypeScriptカバレッジ
npm run test:coverage

# カバレッジレポートを表示
open htmlcov/index.html  # Python
open coverage/lcov-report/index.html  # TypeScript
```

## テストの書き方

### Pythonテスト（pytest）

Pythonフックのテストは`tests/test_hooks.py`に記述します。

```python
def test_my_feature(temp_context_dir, session_logger):
    """
    Test Case: 機能の説明

    Verifies:
    - 検証項目1
    - 検証項目2
    """
    # テストコード
    assert True
```

**利用可能なフィクスチャ:**

- `temp_context_dir`: 一時的なコンテキストディレクトリ
- `session_id`: テスト用セッションID
- `session_logger`: SessionLoggerインスタンス

**テストのベストプラクティス:**

1. テスト名は`test_`で始める
2. docstringで目的と検証項目を明記
3. 日本語コンテンツのテストも含める
4. エラーケースもテストする
5. モックを活用して外部依存を排除

### TypeScriptテスト（Jest）

TypeScriptコンポーネントのテストは`tests/`に`.test.ts`ファイルを作成します。

```typescript
import { describe, test, expect } from '@jest/globals';
import { myFunction } from '../src/core/myModule';

describe('myFunction', () => {
  test('should do something', () => {
    const result = myFunction(input);
    expect(result).toBe(expected);
  });
});
```

**テストのベストプラクティス:**

1. テストファイル名は`*.test.ts`
2. `describe`でグループ化
3. テストケースは明確に記述
4. エッジケースもカバー
5. モック/スタブを適切に使用

### カバレッジ目標

- **最低カバレッジ**: 80%
- **推奨カバレッジ**: 90%以上
- **重要な機能**: 100%を目指す

## コーディング規約

### TypeScript

- **スタイル**: ESLintの設定に従う
- **命名規則**:
  - 変数/関数: camelCase
  - クラス/型: PascalCase
  - 定数: UPPER_SNAKE_CASE
- **型安全**: `any`の使用を避ける
- **コメント**: 複雑なロジックには日本語コメントを追加

### Python

- **スタイル**: PEP 8に準拠
- **命名規則**:
  - 変数/関数: snake_case
  - クラス: PascalCase
  - 定数: UPPER_SNAKE_CASE
- **Type Hints**: 可能な限り型ヒントを追加
- **Docstring**: 関数/クラスには必ずdocstringを記述

### コミットメッセージ

明確で説明的なコミットメッセージを書いてください：

```
<type>: <subject>

<body>

<footer>
```

**Type:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `test`: テスト追加/修正
- `refactor`: リファクタリング
- `chore`: その他の変更

**例:**

```
feat: Add token visualization to markdown output

- Add token count to each conversation entry
- Include session-wide token statistics
- Support Japanese content in token estimation

Closes #42
```

## CI/CD要件

### GitHub Actions

プルリクエストを作成すると、以下のチェックが自動実行されます：

1. **Lint** - コードスタイルチェック
2. **Test** - 全テストの実行
3. **Coverage** - カバレッジレポートの生成
4. **Build** - TypeScriptのビルド確認

### ローカルでCIをシミュレート

プルリクエストを作成する前に、ローカルで以下を確認してください：

```bash
# 1. ビルドが成功するか確認
make build

# 2. 全テストが通るか確認
make test-all

# 3. カバレッジを確認
npm run test:ci
```

### CI要件

- **全テストが成功**: Python + TypeScriptテストが全て成功すること
- **カバレッジ維持**: 新しいコードは80%以上のカバレッジ
- **ビルド成功**: TypeScriptがエラーなくビルドできること
- **型チェック**: TypeScriptの型エラーがないこと

## プルリクエストの作成

### プルリクエストのチェックリスト

プルリクエストを作成する前に、以下を確認してください：

- [ ] ローカルで全テストが通る（`make test-all`）
- [ ] 新機能にはテストが追加されている
- [ ] ドキュメント（README、コメント）が更新されている
- [ ] コミットメッセージが明確である
- [ ] カバレッジが維持/向上している
- [ ] TypeScriptの型エラーがない
- [ ] ビルドが成功する（`make build`）

### プルリクエストのテンプレート

```markdown
## 概要

この変更の目的と内容を簡潔に説明してください。

## 変更内容

- 変更点1
- 変更点2
- 変更点3

## テスト

- [ ] Pythonテストを追加/更新
- [ ] TypeScriptテストを追加/更新
- [ ] 手動テストを実施
- [ ] カバレッジを確認

## チェックリスト

- [ ] ローカルで全テストが通る
- [ ] ドキュメントを更新
- [ ] 型エラーがない
- [ ] ビルドが成功する

## 関連Issue

Closes #<issue番号>
```

## トラブルシューティング

### よくある問題

**1. Pythonテストが失敗する**

```bash
# 依存関係を再インストール
pip install -r requirements-dev.txt --force-reinstall

# キャッシュをクリア
rm -rf .pytest_cache/
```

**2. TypeScriptテストが失敗する**

```bash
# node_modulesを再インストール
rm -rf node_modules/
npm install

# ビルドをクリーンアップ
make clean && make build
```

**3. カバレッジが計算されない**

```bash
# カバレッジディレクトリを削除して再実行
rm -rf .coverage htmlcov/
python3 -m pytest tests/ --cov=src/hooks --cov-report=html
```

**4. フックが動作しない**

```bash
# 実行権限を確認
chmod +x src/hooks/*.py

# シンボリックリンクを確認
ls -la ~/.claude/hooks/

# ビルドが最新か確認
make build
```

## 質問・サポート

問題が解決しない場合は、以下の方法でサポートを受けられます：

- **Issue**: GitHub Issuesで質問を投稿
- **Discussion**: GitHub Discussionsで議論に参加

## ライセンス

このプロジェクトに貢献することで、あなたのコントリビューションがISCライセンスの下で公開されることに同意したものとみなされます。

---

Happy coding!
