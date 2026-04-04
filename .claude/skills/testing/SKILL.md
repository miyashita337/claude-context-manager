---
name: testing
description: TDD + AC駆動の品質管理。実装前にACを定義し、Red→Green→Refactorで品質を担保する
global: true
tools: Bash, Read, Grep, Edit
model: sonnet
---

# Testing Skill（TDD + AC駆動）

**Purpose**: Issue/タスク着手前にAcceptance Criteriaを定義し、TDDワークフローで品質を担保する。

**When to Use**:
- 新機能実装前（AC定義 + テスト先行）
- バグ修正前（再現テスト作成）
- リファクタリング前（既存テストで安全網確認）

---

## Workflow

### Step 1: AC定義（実装前・必須）

Issueや要件からACをGiven/When/Then形式でドラフトする。

**ACテンプレート**:
```markdown
## Acceptance Criteria

| AC-ID | Given | When | Then | 検証コマンド |
|-------|-------|------|------|------------|
| AC-1  | [前提条件] | [操作・入力] | [期待結果] | `pytest tests/test_xxx.py::test_yyy` |
| AC-2  | ...   | ...  | ...  | ... |
```

**例**:
```markdown
| AC-1 | Pythonファイルが存在する | 文字コード検出を実行 | UTF-8と判定される | `pytest tests/test_encoding.py::test_detect_utf8` |
| AC-2 | 空ファイルが与えられる | 文字コード検出を実行 | デフォルト値(UTF-8)を返す | `pytest tests/test_encoding.py::test_empty_file` |
```

**ポイント**:
- 各ACに対応する検証コマンドを必ず書く
- 曖昧な条件（「正しく動く」）は禁止
- AC-IDは連番（AC-1, AC-2, ...）

---

### Step 2: Red（失敗するテスト作成）

ACに基づきテストを先に書く。この時点では実装がないので必ず失敗する。

**Python（pytest）**:
```python
# tests/test_feature.py
def test_given_utf8_file_when_detect_then_returns_utf8():
    """AC-1: UTF-8ファイルを正しく検出する"""
    # Given
    file_path = Path("tests/fixtures/sample_utf8.txt")
    
    # When
    result = detect_encoding(file_path)
    
    # Then
    assert result == "utf-8"
```

**テスト確認コマンド**:
```bash
# 失敗を確認（Red状態であることを明示）
pytest tests/test_feature.py -v
# → FAILED（これが正常）
```

**命名規約**:
- `test_<given>_<when>_<then>` または `test_<状況>_<期待動作>`
- 日本語のコメントでACとの対応を明記

---

### Step 3: Green（実装してテストを通す）

最小限の実装でテストをパスさせる。過剰実装は禁止（YAGNI）。

**実装後確認**:
```bash
# テストがパスすることを確認
pytest tests/test_feature.py -v
# → PASSED

# 既存テストが壊れていないか確認
make test-all
# または
pytest --tb=short
```

**注意**:
- テストをパスさせることだけに集中
- リファクタリングはStep 4で行う

---

### Step 4: Refactor（品質改善）

テストが全てGreenな状態でリファクタリングする。

```bash
# リファクタリング後も全テストがパスすることを確認
make test-all

# カバレッジ確認（目標80%以上）
pytest --cov=src --cov-report=term-missing
```

**リファクタリング対象**:
- 重複コードの除去（DRY）
- 命名の改善
- 複雑な条件式の単純化（KISS）

---

### Step 5: AC検証レポート

全実装完了後、ACを検証してレポートを出力する。

**レポートテンプレート**:
```markdown
## AC検証結果

| AC | 検証内容 | コマンド | 期待 | 実測 | 判定 |
|----|---------|---------|------|------|------|
| AC-1 | UTF-8検出 | `pytest tests/test_encoding.py::test_detect_utf8` | PASSED | PASSED | PASS |
| AC-2 | 空ファイル | `pytest tests/test_encoding.py::test_empty_file` | PASSED | PASSED | PASS |

全体: 2/2 PASS
```

---

## 場面別フロー

### 新機能実装

```
Issue確認 → AC定義（Given/When/Then） → テスト作成（Red）
→ 最小実装（Green） → リファクタリング → AC検証レポート
```

### バグ修正

```
バグ再現テスト作成（Red） → 修正（Green）
→ 関連テスト確認 → AC検証レポート
```

### リファクタリング

```
既存テスト確認（全Greenを確認）→ リファクタリング
→ 全テスト再確認 → カバレッジ確認
```

---

## よく使うコマンド

```bash
# テスト実行（プロジェクト標準）
make test-all

# 特定テストファイルのみ
pytest tests/test_xxx.py -v

# 特定テスト関数のみ
pytest tests/test_xxx.py::test_function_name -v

# カバレッジ付き実行
pytest --cov=src --cov-report=term-missing

# 失敗時に即停止
pytest -x

# キーワードでフィルタ
pytest -k "encoding" -v
```

---

## Anti-Patterns

### ❌ 実装後にテストを書く

```markdown
❌ Wrong: [実装] → [テスト] → [テスト修正でパス合わせ]
✅ Correct: [AC定義] → [テスト] → [実装] → [Refactor]
```

### ❌ 曖昧なAC

```markdown
❌ Wrong: "正しく動くこと"
✅ Correct: "UTF-8ファイルに対してdetect_encodingが'utf-8'を返すこと"
```

### ❌ 検証コマンドなしのAC

```markdown
❌ Wrong: AC定義のみ → 目視確認
✅ Correct: 各ACに対して実行可能なコマンドで決定的に検証
```

---

## Related Resources

- `.claude/PITFALLS.md` - テスト関連エラーパターン
- `rules/general/testing.md` - テストルール（グローバル）
- `rules/general/acceptance-criteria.md` - AC検証ルール（グローバル）

---

## Version History

- 2026-04-04: Initial creation for Issue #113
