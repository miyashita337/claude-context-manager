---
title: "公式ドキュメントを読まないAIの防御方法"
emoji: "🛡️"
type: "tech"
topics: ["claude", "ai", "testing", "devops"]
published: false
---

# 公式ドキュメントを読まないAIの防御方法

Claude Code に `.claude/hooks/hooks.json` という設定ファイルは存在しない。

しかし、AI（Claude）は自信満々にそのパスを生成し、私はそれを信じて実装した。テストは全て通った。だが、hookは一度も実行されていなかった。

## 何が起きたか

Claude Code のコンテキスト保存システムを開発中、hookが動作しないことに気づいた。原因を調べると、設定ファイルのパスが間違っていた。

```bash
# ❌ AIが生成した非公式パス
.claude/hooks/hooks.json

# ✅ 公式ドキュメントに記載された正しいパス
.claude/settings.json
```

[[画像: 非公式パスと公式パスの比較スクリーンショット]]

致命的なのは、**単体テストが全てパスしていた**ことだ。テストは「設定ファイルが存在するか」だけをチェックし、「hookが実際に実行されるか」は検証していなかった。典型的な Silent Failure である。

## なぜAIは間違えたのか

AIは公式ドキュメントを参照せず、過去の学習データから「もっともらしいパス」を推測した。`.claude/hooks/hooks.json` は確かに存在しそうなパスだ。しかし、それは**ハルシネーション（もっともらしい嘘）**だった。

問題の本質は3つ：

1. **AIは自信満々に間違える** - 公式パスを知らず、推測で答える
2. **テストが不十分** - 設定の存在だけチェック、実行は検証せず
3. **ナレッジが散逸** - 同じエラーを繰り返す仕組みがない

## 解決策：3層防御アーキテクチャ

再発防止のため、以下の3層防御を構築した。

### Layer 1: PITFALLS.md（grep可能なナレッジDB）

発生したエラーをMarkdown形式で記録する。

```markdown
### GIT-002: 非公式フックパス

**Error Signature**: Hook not executing despite proper configuration

**Context**: `.claude/hooks/hooks.json` (非公式) を使用

**Solution**:
`.claude/hooks/hooks.json` → `.claude/settings.json` に移行

**Prevention**: `/fact-check` で公式パスを検証
```

[[画像: PITFALLS.mdの実際のエントリ表示]]

**なぜgrep可能である必要があるか？**

当初、JSONやSQLiteも検討したが、Markdown + grepにした理由は2つ：

1. **LLMの「Lost in the Middle」問題** - 長いJSONを読むと中間部分を見落とす。Markdownなら`grep "エラーメッセージ"`で該当箇所を直接抽出できる
2. **検索速度** - 小規模（0-50エントリ）なら`grep`が最速。0.1秒未満で検索完了

この設計により、AIは「エラーメッセージで grep → 解決策を発見」を自動実行できる。

### Layer 2: Skills（AIハルシネーション検出）

Claude Code の Skills 機能で、3つの検証ワークフローを実装。

```yaml
---
name: fact-check
description: 公式ドキュメント照合
tools: WebSearch, WebFetch, Read, Grep
---
```

**`/fact-check`の仕組み**：

```
1. WebSearch で公式ドキュメントを検索
   ↓
2. WebFetch でドキュメント内容を取得
   ↓
3. 現在の実装（Read）と比較
   ↓
4. 差異をレポート
```

[[画像: /fact-check実行時のスクリーンショット]]

これにより、「AIが生成したパスは公式か？」を**実装前に検証**できる。

**`/pre-commit`** は `make pre-git-check` を実行し、エラーを PITFALLS.md で自動検索・解決する。

**`/git-workflow`** は初期コミット時の HEAD エラーなど、git のエッジケースを自動で回避する。

### Layer 3: E2Eテスト（実行の検証）

単体テストでは不十分だった。E2Eテストで「hookが実際に実行されるか」を検証：

```python
def test_hook_actually_executes():
    """hookが実際に実行されることを確認"""
    result = subprocess.run(
        ["python", "src/hooks/user-prompt-submit.py"],
        input=json.dumps({"prompt": "test"}),
        capture_output=True
    )
    assert result.returncode == 0
    assert "log file created"  # 実行の証拠を確認
```

**テスト結果**: 98/98 PASS（既存64 + 新規34テスト）

[[画像: pytest実行結果のスクリーンショット]]

## アーキテクチャ全体図

```
エラー発生
  ↓
PITFALLS.md検索（grep < 0.1秒）
  ↓
解決策発見 → Skills自動適用（/pre-commit）
  ↓
E2Eテストで検証
```

[[画像: 3層防御アーキテクチャ図]]

Skills が PITFALLS.md を自動参照し、ユーザーは「/pre-commit と入力するだけ」でエラー解決できる。

## 成果

4つのエラーパターンを PITFALLS.md に記録：

- **GIT-001**: 初期コミット HEAD エラー → `/git-workflow` が自動回避
- **GIT-002**: 非公式パス問題 → `/fact-check` で検出
- **HOOK-001**: テスト不足 → E2E テストで解決
- **SEC-001**: 機密情報検出 → `/pre-commit` で自動 unstage

次回から同じエラーは **5秒以内に解決** できる。

## まとめ：AIの実装を盲信しない

AIは強力だが、公式ドキュメントを読まない。ハルシネーションは避けられない。

**3つの教訓**：

1. **ファクトチェック** - `/fact-check` で公式パスを検証
2. **ナレッジ蓄積** - PITFALLS.md でエラーを grep 可能に
3. **実行の検証** - 単体テストだけでなく E2E テストで確認

同じパターンは他のプロジェクトでも応用できる。特に「AIが生成したコード」を使う場合、この3層防御は有効だ。

あなたのプロジェクトでも、AIのもっともらしい嘘に騙されていないか確認してみてほしい。

---

## リンク

- **GitHubリポジトリ**: https://github.com/miyashita337/claude-context-manager
- **実装PR**: https://github.com/miyashita337/claude-context-manager/pull/1
  _(PITFALLS.md + Skills + テストの完全な実装)_

**文字数**: 約1850字
