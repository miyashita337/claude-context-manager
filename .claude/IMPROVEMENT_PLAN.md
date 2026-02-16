# Claude Context Manager - 改善実装プラン

## 📅 作成日: 2026-02-15
## 📅 最終更新: 2026-02-15

## 🎯 目的
今回の開発で発生したエラー（APIキー露出、HEADエラー、.gitignore不備）を防止し、
安定した高速開発を実現する。

---

## ✅ 実装状況

### P0: 再発防止策（緊急） - ✅ 完了 (2026-02-15)

**実装内容**:
- ✅ PITFALLS.md作成（エラーパターンデータベース、4初期エントリ）
- ✅ Skills作成（/fact-check, /pre-commit, /git-workflow）
- ✅ テストスイート作成（34テスト、全PASS）
- ✅ CLAUDE.md更新（Skills使用方法、エラー解決ワークフロー）

**成果**:
- GIT-001（初期コミットHEADエラー）→ 自動検出・解決可能
- GIT-002（非公式パス）→ /fact-checkで検証可能
- HOOK-001（テスト不足）→ E2Eテスト追加で検出
- SEC-001（機密情報検出）→ /pre-commitで自動防止

**テスト結果**:
- `tests/test_pitfalls.py`: 12/12 PASS
- `tests/test_skills.py`: 13/13 PASS (2 warnings: 推奨サイズ超過)
- `tests/test_e2e_error_resolution.py`: 9/9 PASS
- **合計**: 34/34 PASS ✅

**次のステップ**:
- [ ] 実地テスト（新規リポジトリで初期コミットテスト）
- [ ] ドキュメント完全性チェック
- [ ] CI/CD統合（Phase 1へ）

---

## Phase 1: 即座実装（優先度：🔴 CRITICAL）

### 1.1 Pre-Git セキュリティチェックスクリプト
**目的**: Git操作前に機密情報を自動検出

**実装**: `scripts/pre-git-check.sh`
- .gitignore完全性チェック
- APIキー検出（OpenAI, Gemini, AWS, GitHub）
- 不要ファイル検出（__pycache__, *.pyc, *.backup）
- 初回コミット判定

**使用方法**:
```bash
make pre-git-check  # Git操作前に必ず実行
```

**期待効果**: APIキー露出リスク 90%削減

---

### 1.2 Makefile統合
**目的**: ワンコマンドでセキュリティチェック実行

**追加ターゲット**:
```makefile
.PHONY: pre-git-check security-scan git-safe-push

pre-git-check:
	@bash scripts/pre-git-check.sh

security-scan:
	@bash scripts/security-scan.sh

git-safe-push: pre-git-check
	@git push origin main
```

---

### 1.3 CLAUDE.md 更新
**目的**: AIエージェント向けGit操作ガイドライン

**追加セクション**:
```markdown
# Git操作ガイドライン（BLOCKING REQUIREMENT）

## 必須ルール
1. Git操作前に必ず `make pre-git-check` を実行
2. 以下は必ずユーザー確認:
   - git push（特にpublicリポジトリ）
   - 初回 git commit
   - 10ファイル以上の操作
3. エラー3回連続で処理停止 → 状況整理 → ユーザー確認
4. セキュリティ > ユーザー確認 > 実行（優先順位）
```

---

### 1.4 Git Hooks インストール
**目的**: コミット前に自動チェック

**実装**: `.git/hooks/pre-commit`
```bash
#!/usr/bin/env bash
# 自動的にセキュリティチェックを実行

bash scripts/pre-git-check.sh || {
    echo "❌ Pre-commit checks failed. Fix issues and retry."
    exit 1
}
```

**インストール**:
```bash
make git-hooks  # 一度だけ実行
```

---

## Phase 2: 短期実装（1週間以内）

### 2.1 品質ゲートフレームワーク
**実装**: `scripts/quality_gates.py` + `.quality-gates.yaml`

**機能**:
- Security Gate（必須）
- Code Quality Gate（推奨）
- Git Hygiene Gate（必須）
- Integration Gate（必須）

**使用方法**:
```bash
python3 scripts/quality_gates.py pre-commit
python3 scripts/quality_gates.py pre-push
```

---

### 2.2 エラーハンドリングフレームワーク
**実装**: `src/hooks/shared/error_handler.py`

**機能**:
- 統一されたエラー分類（ValidationError, SecurityError）
- 詳細なエラーコンテキスト
- 自動リカバリー提案

---

### 2.3 GitHub Actions セキュリティスキャン
**実装**: `.github/workflows/security.yml`

**機能**:
- Gitleaks（シークレット検出）
- 依存関係脆弱性スキャン（npm audit, safety）
- CodeQL（SAST）
- .gitignore検証

---

## Phase 3: 中期実装（2週間以内）

### 3.1 自動テストスイート
**実装**: `tests/run-tests.sh`

**テストケース**:
- 初回コミット時のHEADエラー対応
- 不要ファイル検出
- セキュリティスキャン（.envファイル）

---

### 3.2 プロジェクトテンプレート
**実装**: `scripts/setup-project.sh`

**機能**:
- 完全な.gitignore自動生成
- .env.example作成
- Git hooks自動設定
- 冪等性保証（何度実行してもOK）

---

### 3.3 ドキュメント体系
**作成ファイル**:
```
docs/
├── adr/                        # Architecture Decision Records
│   └── ADR-001-hook-error-handling.md
├── checklists/                 # チェックリスト
│   ├── pre-git-checklist.md
│   └── code-review-checklist.md
├── SECURITY_GUIDELINES.md      # セキュリティガイドライン
└── TECHNICAL_DEBT.md           # 技術的負債管理
```

---

## Phase 4: 長期改善（1ヶ月以内）

### 4.1 Three-Tier Approach（速度と安定性の両立）

```
Fast Track    → ドキュメント、テスト → 即実行
Standard Track → コード変更 → 事前チェック
Careful Track  → Git操作 → 完全チェック + ユーザー確認
```

**自動判別**:
```python
def assess_risk_level(operation):
    if 'git push' in operation or '.env' in files:
        return 'CAREFUL'  # 必ずユーザー確認
    elif 'git commit' in operation or len(files) > 10:
        return 'STANDARD'  # 事前チェックのみ
    else:
        return 'FAST'  # 即実行
```

---

### 4.2 AgentTeam標準化
**目的**: 複数Agentの効率的な活用

**実装**: `.claude/agent-team-config.yaml`
```yaml
agents:
  security:
    role: "セキュリティレビュー"
    trigger: "git操作前、機密情報検出時"

  devops:
    role: "CI/CDとインフラ"
    trigger: "ワークフロー変更時"

  qa:
    role: "品質保証"
    trigger: "テスト失敗時、エラーループ時"

  pm:
    role: "プロセス改善"
    trigger: "新機能計画時、振り返り時"

  senior-engineer:
    role: "アーキテクチャレビュー"
    trigger: "大規模リファクタリング時"
```

---

## 実装優先順位（AgentTeam総意）

**優先順位**: 安定性（C）> 開発速度（B）> セキュリティ（A）

### 🔴 P0: 即座（今日中）✅ **完了**
- [x] **完了** .gitignore更新（2026-02-15）
- [x] **完了** AgentTeam有効化（settings.json）（2026-02-15）
- [x] **完了** `scripts/pre-git-check.sh`作成（2026-02-15）
- [x] **完了** Makefile `pre-git-check`ターゲット追加（2026-02-15）
- [x] **完了** Makefile `git-clean`ターゲット追加（2026-02-15）
- [x] **完了** Makefile `git-safe-push`ターゲット追加（2026-02-15）
- [x] **完了** CLAUDE.md Git操作ガイドライン追加（グローバル）（2026-02-15）
- [x] **完了** CLAUDE.md プロジェクト固有ガイドライン作成（2026-02-15）

### 🟡 P1: 短期（1週間）✅ **完了 (2026-02-15)**
- [x] **完了** Git hooks設定（pre-commit）（2026-02-15）
- [x] **完了** GitHub Actions セキュリティスキャン（2026-02-15）
- [x] **完了** 品質ゲートフレームワーク（2026-02-15）
- [x] **完了** Hook設定の公式パス移行（2026-02-15）✨
- [x] **完了** Hook validation/backup/restore スクリプト（2026-02-15）✨
- [x] **完了** 包括的なHookテスト追加（51個）（2026-02-15）✨

### 🟢 P2: 中期（2週間）
- [ ] **未着手** 自動テストスイート
- [ ] **未着手** プロジェクトテンプレート（setup-project.sh）
- [ ] **未着手** ドキュメント体系整備

### 🔵 P3: 長期（1ヶ月）
- [ ] **未着手** Three-Tier Approach実装
- [ ] **未着手** AgentTeam標準化（agent-team-config.yaml）
- [ ] **未着手** メトリクス収集と可視化

---

## 成功指標（KPI）

### セキュリティ
- APIキー露出: 0件/月（目標）
- セキュリティスキャン実行率: 100%

### 品質
- エラーループ発生: 月1回以下
- Git操作成功率: 95%以上（初回で成功）

### 開発効率
- セットアップ時間: 5分以内
- デプロイ時間: 10分以内
- エラー修正時間: 10分以内/エラー

---

## ユーザーへの質問

実装を進める前に、以下を確認させてください：

### Q1: 実装範囲
今回どこまで実装しますか？
- [ ] P0のみ（今日中に完了可能）
- [ ] P0 + P1（1週間で完了）
- [ ] 全フェーズ（段階的に実装）

### Q2: 優先事項
最も重要視することは？
- [ ] セキュリティ（APIキー露出防止）
- [ ] 開発速度（自動化で高速化）
- [ ] 安定性（エラー削減）
- [ ] すべてバランス良く

### Q3: AgentTeam活用
今後のAgentTeam活用について：
- [ ] 必要に応じて個別起動
- [ ] 定期的な振り返りで活用
- [ ] 重要な意思決定時に活用

### Q4: ドキュメント
どのドキュメントを優先的に作成すべきですか？
- [ ] CLAUDE.md（AIエージェント向けガイドライン）
- [ ] SECURITY_GUIDELINES.md（セキュリティガイド）
- [ ] チェックリスト（日常的に使用）
- [ ] すべて

---

## 次のアクション

ユーザーの回答に基づいて、以下を実施します：

1. **即座実装**: P0項目のスクリプト作成
2. **検証**: 実際のGit操作で動作確認
3. **ドキュメント化**: CLAUDE.md更新
4. **展開**: プロジェクトテンプレート化

お答えいただければ、すぐに実装を開始します。
