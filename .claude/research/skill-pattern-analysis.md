# 既存Skillパターン分析

**分析日**: 2026-02-16
**対象**: fact-check, git-workflow, pre-commit

---

## 📊 基本統計

| Skill | 行数 | 主要ツール | モデル |
|-------|------|------------|--------|
| fact-check | 475行 | WebSearch, WebFetch, Read, Grep | sonnet |
| git-workflow | 674行 | Bash, Read, Grep | sonnet |
| pre-commit | 509行 | Bash, Read, Grep | sonnet |
| **合計** | **1658行** | - | - |

---

## 🎯 共通パターン

### 1. YAMLフロントマター構造

**全Skillで統一されたフォーマット**:
```yaml
---
name: skill-name          # kebab-case
description: One-line description (短い説明)
tools: Tool1, Tool2, Tool3  # カンマ区切り
model: sonnet             # sonnet/opus/haiku
---
```

**フィールド詳細**:
- `name`: スキル名（kebab-case、例: `pre-commit`, `fact-check`）
- `description`: 1行の簡潔な説明（50-80文字）
- `tools`: 使用するツールのリスト（Bash, Read, Grep, WebSearch, WebFetchなど）
- `model`: 推奨モデル（全て`sonnet`を使用）

---

### 2. ドキュメント構造

**全Skillが以下の構造を持つ**:

```markdown
# [Skill Name] Skill

**Purpose**: [1-2文でSkillの目的]

**When to Use**:
- [使用シーン1]
- [使用シーン2]
- [使用シーン3]

**Core Functionality/Key Features**:
- [主要機能1]
- [主要機能2]

---

## Workflow

### Step 1: [ステップタイトル]

[ステップの説明]

**Tools**:
```python
ツールの使用例
```

**Outcomes**:
- ✅ [成功時の結果]
- ❌ [失敗時の結果]

---

### Step 2-N: [続くステップ]

...

---

## Examples

### Example 1: [例のタイトル]

[具体的な使用例]

---

## Best Practices

### 1. [ベストプラクティス1]

---

## Anti-Patterns

### ❌ Don't: [やってはいけないこと]

---

## Related Resources

- [関連ファイル1]
- [関連ファイル2]

---

## Version History

- YYYY-MM-DD: [変更履歴]
```

---

### 3. ワークフローパターン（全Skill共通）

**4段階のワークフロー**:

#### Phase 1: 入力取得・状況確認
- **fact-check**: ユーザーの質問を理解
- **git-workflow**: Pre-flight safety check（`make pre-git-check`, `git status`）
- **pre-commit**: Pre-commit checkを実行（`make pre-git-check`）

#### Phase 2: 分析・調査
- **fact-check**: 公式ドキュメント検索（WebSearch）
- **git-workflow**: Staging area検証、初期コミット検出
- **pre-commit**: エラー解析、PITFALLS.md検索

#### Phase 3: 処理・修正
- **fact-check**: ドキュメント取得・解析（WebFetch）
- **git-workflow**: エッジケース処理、安全なコミット実行
- **pre-commit**: 自動修正適用、再チェック

#### Phase 4: 結果報告
- **全Skill**: 構造化されたレポート生成
- 共通フォーマット: Status + Details + Next Steps + Reference

---

### 4. ツール使用パターン

#### Bash Tool
**用途**: コマンド実行、システム操作

**使用例**:
```python
# fact-check: 使用なし
# git-workflow:
Bash(command='make pre-git-check', description='Run pre-commit safety checks')
Bash(command='git status', description='Check working tree status')
Bash(command='git rev-parse HEAD >/dev/null 2>&1 && echo "HAS_HEAD" || echo "NO_HEAD"')

# pre-commit:
Bash(command='make pre-git-check', description='Run pre-commit safety checks')
Bash(command='git rm --cached config.py', description='Unstage file with secrets')
```

**パターン**:
- 必ず`description`を指定（ユーザーに何をしているか明示）
- エラーハンドリング（`exit code`チェック）
- 長時間実行コマンドの進捗表示

---

#### Read Tool
**用途**: ファイル内容の読み込み

**使用例**:
```python
# fact-check:
Read(file_path='.claude/settings.json')
Read(file_path='.claude/hooks/hooks.json')  # 非推奨パスのチェック

# git-workflow:
Read(file_path='.claude/PITFALLS.md')  # エラーパターン参照

# pre-commit:
Read(file_path='.claude/PITFALLS.md')  # ソリューション検索
```

**パターン**:
- 絶対パス使用
- 設定ファイル、ドキュメント、ログの読み込み
- エラーDB（PITFALLS.md）の参照

---

#### Grep Tool
**用途**: パターン検索、エラー検出

**使用例**:
```python
# fact-check:
Grep(pattern='hooks', glob='**/*.json', output_mode='files_with_matches')
Grep(pattern='.claude/hooks/hooks.json', output_mode='content')

# git-workflow:
Grep(pattern='fatal: ambiguous argument', path='.claude/PITFALLS.md',
     output_mode='content', -B=5, -A=20)

# pre-commit:
Grep(pattern='OpenAI API key detected', path='.claude/PITFALLS.md',
     output_mode='content', -B=5, -A=20)
Grep(pattern='GIT-001', path='.claude/PITFALLS.md', output_mode='content', -A=30)
```

**パターン**:
- `output_mode='content'`: 内容表示（コンテキスト付き）
- `output_mode='files_with_matches'`: ファイルパスのみ
- `-B`, `-A`: コンテキスト行数指定（エラーIDと解決策を含める）
- PITFALLS.md検索時: `-B=5, -A=20`（標準）

---

#### WebSearch/WebFetch (fact-checkのみ)
**用途**: 公式ドキュメント検索・取得

**使用例**:
```python
# WebSearch:
WebSearch(query='Claude Code hooks configuration site:docs.claude.com 2026')

# WebFetch:
WebFetch(
    url='https://docs.claude.com/claude-code/hooks',
    prompt='Extract the official hook configuration path and show example configuration'
)
```

**パターン**:
- `site:docs.claude.com`で公式ドキュメントに限定
- 年を含める（`2026`）
- WebFetchのpromptは具体的に（何を抽出するか明示）

---

### 5. エラーハンドリングパターン

#### PITFALLS.md統合（git-workflow, pre-commit）
```markdown
**フロー**:
1. エラー検出
2. Grepで PITFALLS.md 検索
   - エラーシグネチャで検索
   - または エラーID で検索
3. 解決策を抽出
4. 自動修正（安全な場合）
5. ユーザー報告

**検索戦略**:
- 直接マッチ: エラーシグネチャで検索
- 部分マッチ: キーワードで検索
- カテゴリ検索: `## Security Errors`などで検索
```

#### /fact-check統合（fact-check自身、他Skillからも利用可能）
```markdown
**フロー**:
1. 実装詳細の不確実性検出
2. WebSearchで公式ドキュメント検索
3. WebFetchで詳細取得
4. 現在の実装と比較
5. 差異レポート生成

**使用タイミング**:
- 新機能実装前
- 予期しない動作発生時
- 設定パス・フォーマット不明時
```

#### エラーループ防止
```markdown
**全Skillで実装**:
- 最大3回のリトライ
- 同じエラーが3回連続 → 処理停止
- ユーザーに状況報告 + 手動介入要請

**実装例**:
retry_count = 0
max_retries = 3
while retry_count < max_retries:
    result = attempt_fix()
    if success:
        break
    retry_count += 1
    if retry_count >= max_retries:
        report_to_user("Manual intervention required")
```

---

### 6. レポートフォーマット

**全Skillが構造化レポートを生成**:

```markdown
## [Skill Name] Report

### Status
[✅ PASSED / ⚠️ WARNING / ❌ FAILED] [一行サマリー]

### [Main Content Section]
[詳細内容]

### [Actions/Fixes/Results]
[実行した処理または結果]

### Manual Steps Required (該当時)
1. [ ] [ステップ1]
2. [ ] [ステップ2]

### Next Steps
[ユーザーへの指示]

### Reference
- [関連ドキュメント]
- [PITFALLS.mdエントリ]
```

**ステータス記号の使い方**:
- ✅ `PASSED/CORRECT`: 成功、問題なし
- ⚠️ `WARNING/PARTIALLY_CORRECT`: 警告、一部問題あり
- ❌ `FAILED/INCORRECT`: 失敗、問題あり
- ℹ️ 情報提供
- 🔄 再試行中

---

### 7. Examples セクションパターン

**全Skillが2-3個の実例を提供**:

```markdown
### Example 1: [シナリオタイトル]

**Question/Initial State**:
[初期状態または質問]

**Step 1 - [アクション]**:
[実行内容]

**Step 2 - [アクション]**:
[実行内容]

**Step N - Report**:
[最終レポート]
```

**例の種類**:
- **成功ケース**: 全てがうまくいった場合
- **エラーケース**: エラーが発生し、自動修正された場合
- **複雑ケース**: 複数ステップが必要な場合

---

### 8. Best Practices / Anti-Patterns

#### Best Practices セクション
```markdown
## Best Practices

### 1. [プラクティス1のタイトル]

[説明と実装例]

---

### 2. [プラクティス2のタイトル]

[説明と実装例]
```

**共通のベストプラクティス**:
- 実行前の確認（pre-flight check）
- エラーは即座に報告
- 自動修正は安全な場合のみ
- PITFALLS.md/公式ドキュメントの活用
- ユーザーへの透明性（何をしているか明示）

#### Anti-Patterns セクション
```markdown
## Anti-Patterns

### ❌ Don't: [やってはいけないこと]

**Wrong**:
[間違った方法]

**Correct**:
[正しい方法]

**Problem**:
[なぜ間違っているか]
```

**共通のアンチパターン**:
- ユーザーへの通知なしの自動修正
- エラーループ（無限リトライ）
- 警告の無視
- ドキュメント未確認での実装

---

## 🔧 ツール使用頻度

| ツール | fact-check | git-workflow | pre-commit | 合計 |
|--------|-----------|--------------|-----------|------|
| Bash | 0 | 多数 | 多数 | ⭐⭐⭐ |
| Read | 中 | 中 | 中 | ⭐⭐⭐ |
| Grep | 多数 | 多数 | 多数 | ⭐⭐⭐ |
| WebSearch | 多数 | 0 | 0 | ⭐ |
| WebFetch | 多数 | 0 | 0 | ⭐ |

**観察**:
- **Bash, Read, Grep**: 全Skillで使用される基本ツール
- **WebSearch/WebFetch**: 公式ドキュメント検証専用（fact-checkのみ）

---

## 📐 Skill設計の黄金律

### 1. **明確な目的** (Purpose)
各Skillは1つの明確な目的を持つ:
- **fact-check**: 公式ドキュメント照合
- **git-workflow**: 安全なGit操作ガイド
- **pre-commit**: 自動エラー検出・修正

### 2. **段階的ワークフロー** (Step-by-Step)
全てのSkillは4-6ステップのワークフロー:
1. 入力/状況確認
2. 分析
3. 処理
4. 結果報告
5. (オプション) 再試行
6. (オプション) 最終報告

### 3. **具体的な例** (Examples)
各Skillは2-3個の実例を提供:
- 成功ケース
- エラーケース
- 複雑ケース

### 4. **エラーハンドリング** (Error Handling)
全Skillがエラーループ防止を実装:
- 最大3回リトライ
- ユーザー報告
- 手動介入要請

### 5. **ドキュメント連携** (Documentation Integration)
- PITFALLS.md: エラーパターンDB
- /fact-check: 公式ドキュメント照合
- CLAUDE.md: プロジェクトガイドライン

### 6. **透明性** (Transparency)
ユーザーに何をしているか常に明示:
- Bashの`description`パラメータ
- ステップごとの説明
- 構造化レポート

---

## 🎨 新Skill設計への適用

### Codex Skill設計指針

**YAMLフロントマター**:
```yaml
---
name: codex
description: Analyze codebase using Codex CLI with real-time progress
tools: Bash, Read, Grep
model: sonnet
---
```

**ワークフロー**:
1. **Step 1**: Prepare Analysis（スコープ決定）
2. **Step 2**: Execute Codex CLI（Bashでcodex実行）
3. **Step 3**: Process Results（結果解析）
4. **Step 4**: Generate Report（レポート生成）

**ツール使用**:
- **Bash**: `codex analyze .`, `codex search "pattern"`
- **Read**: `codex.config.json`読み込み
- **Grep**: 結果からパターン抽出

---

### ccusage Skill設計指針

**YAMLフロントマター**:
```yaml
---
name: ccusage
description: Analyze Claude Code session tokens and detect compact events
tools: Bash, Read, Grep
model: sonnet
---
```

**ワークフロー**:
1. **Step 1**: Discover Session Files（`~/.claude/sessions/`検索）
2. **Step 2**: Analyze Token Usage（トークンカウント）
3. **Step 3**: Detect Compact Events（compact検出）
4. **Step 4**: Calculate Diffs（差分計算）
5. **Step 5**: Measure Context Length（コンテキスト長測定）
6. **Step 6**: Generate Report（レポート生成）

**ツール使用**:
- **Bash**: `ccusage analyze`, `find ~/.claude/sessions/`
- **Read**: セッションJSONLファイル読み込み
- **Grep**: compactマーカー検索、エラーパターン検索

---

## 📋 チェックリスト: 新Skill作成時

設計フェーズ:
- [ ] YAMLフロントマターを定義
- [ ] Purpose（目的）を1-2文で明確化
- [ ] When to Use（使用シーン）を3-5個列挙
- [ ] 4-6ステップのワークフローを設計
- [ ] 使用するツールを特定
- [ ] エラーハンドリング戦略を定義

実装フェーズ:
- [ ] SKILL.mdを作成（上記構造に従う）
- [ ] Workflowセクションを実装
- [ ] 各ステップにツール使用例を追加
- [ ] Examplesセクションを追加（2-3個）
- [ ] Best Practicesを追加
- [ ] Anti-Patternsを追加
- [ ] Related Resourcesを追加
- [ ] Version Historyを追加

テストフェーズ:
- [ ] 実際のコマンドをテスト
- [ ] エラーケースをテスト
- [ ] エラーループ防止を確認
- [ ] レポートフォーマットを確認
- [ ] ドキュメントの完全性を確認

---

## 🔗 参考ファイル

- `.claude/skills/fact-check/SKILL.md` (475行)
- `.claude/skills/git-workflow/SKILL.md` (674行)
- `.claude/skills/pre-commit/SKILL.md` (509行)
- `.claude/PITFALLS.md` (エラーパターンDB)
- `.claude/CLAUDE.md` (プロジェクトガイドライン)

---

## 📊 統計サマリー

- **総行数**: 1658行
- **平均行数**: 553行/Skill
- **最大行数**: 674行 (git-workflow)
- **最小行数**: 475行 (fact-check)
- **共通構造要素**: 10個（YAMLフロントマター、Purpose、When to Use、Workflow、Examples、Best Practices、Anti-Patterns、Related Resources、Version History、Tools使用例）

---

**分析完了日**: 2026-02-16
**次のステップ**: Phase 2（設計）でこのパターンをCodex/ccusage Skillsに適用
