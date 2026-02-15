# Claude Context Manager - セッション起動時チェックリスト

## 🚀 クイックスタート（自動化版）

新しいセッションを開始したら、以下のコマンドを実行してください：

```bash
make startup-check
```

すべて ✅ なら、Claude Context Manager は正常に動作しています！

---

## 📋 手動チェック（詳細版）

自動化スクリプトで問題が検出された場合、または詳細を確認したい場合は、以下の手動チェックを実行してください。

新しいセッションを開始したら、以下のチェックを実行してください。
このチェックリストをClaude（メイン）にコピー&ペーストして実行を依頼できます。

---

## 📋 セッション起動時チェック

以下の項目を順番に確認してください：

### 1. Hook動作確認

以下のコマンドを実行して、hookが正常に動作しているか確認してください：

```bash
# UserPromptSubmit hookのテスト（正常なJSON）
echo '{"session_id": "startup-check-001", "prompt": "起動確認テスト"}' | python3 /Users/harieshokunin/claude-context-manager/src/hooks/user-prompt-submit.py

# 期待される出力: {"hookSpecificOutput": {"status": "logged", "session_id": "startup-check-001", "total_tokens": ...}}
```

```bash
# UserPromptSubmit hookのテスト（空stdin）
echo '' | python3 /Users/harieshokunin/claude-context-manager/src/hooks/user-prompt-submit.py

# 期待される出力: {"hookSpecificOutput": {"status": "skipped", "reason": "empty stdin"}}
```

```bash
# PostToolUse hookのテスト
echo '{"session_id": "startup-check-002", "tool_name": "Read", "tool_input": {"file": "test.txt"}, "tool_response": "test content"}' | python3 /Users/harieshokunin/claude-context-manager/src/hooks/post-tool-use.py

# 期待される出力: {"hookSpecificOutput": {"status": "logged", "session_id": "startup-check-002", "total_tokens": ...}}
```

**✅ 確認ポイント**:
- すべてのコマンドがエラーなく終了する
- `status: "logged"` または `status: "skipped"` が返される
- JSONDecodeErrorが発生しない

---

### 2. ログファイル作成確認

```bash
# 一時ログディレクトリの確認
ls -la ~/.claude/context-history/.tmp/

# テストで作成されたログファイルの確認
cat ~/.claude/context-history/.tmp/session-startup-check-001.json
cat ~/.claude/context-history/.tmp/session-startup-check-002.json
```

**✅ 確認ポイント**:
- `.tmp/` ディレクトリが存在する
- `session-*.json` ファイルが作成されている
- ファイル内容がJSON Lines形式（1行1JSON）で保存されている

---

### 3. エラーログの確認

```bash
# 最近のエラーログを確認（存在する場合）
tail -n 50 ~/.claude/hook-debug.log 2>/dev/null || echo "エラーログなし（正常）"

# デバッグログの確認
tail -n 20 /tmp/user-prompt-submit-debug.log 2>/dev/null || echo "デバッグログなし"
tail -n 20 /tmp/post-tool-use-debug.log 2>/dev/null || echo "デバッグログなし"
```

**✅ 確認ポイント**:
- `JSONDecodeError` や `stdin is empty` エラーが**出ていない**こと
- エラーログファイルが存在しないか、古いエラーのみであること

---

### 4. Hook設定の確認

```bash
# プロジェクトのhook設定を確認
cat /Users/harieshokunin/claude-context-manager/.claude/hooks/hooks.json | python3 -m json.tool

# グローバル設定を確認（プロジェクトhookが重複していないか）
cat ~/.claude/settings.json | python3 -m json.tool | grep -A 20 '"hooks"'
```

**✅ 確認ポイント**:
- プロジェクト設定に `UserPromptSubmit`, `PostToolUse`, `Stop` が存在する
- グローバル設定に claude-context-manager のhookが**重複していない**こと

---

### 5. テストスイートの実行（オプション）

```bash
# 全テストを実行
cd /Users/harieshokunin/claude-context-manager
python3 -m pytest tests/test_hooks.py -v

# 期待される結果: 12/13 テストがPASS（1つのstop.pyテストは既知の問題）
```

**✅ 確認ポイント**:
- `test_stdin_empty_handling`: PASSED
- `test_stdin_whitespace_only_handling`: PASSED
- 全体で 12個以上のテストがPASS

---

### 6. 実際のセッションでの動作確認

現在のセッションでテストメッセージを送信して、hookが動作しているか確認：

```bash
# 現在のセッションIDを確認（Claude Codeが自動的に設定）
echo "現在のセッションで何かメッセージを送信してください"

# その後、以下で最新のログを確認
ls -lt ~/.claude/context-history/.tmp/ | head -n 5
```

**✅ 確認ポイント**:
- メッセージ送信後、`.tmp/session-*.json` ファイルが更新される
- ファイル内に送信したメッセージが記録されている

---

## 🚨 トラブルシューティング

### エラーが発生した場合

1. **JSONDecodeError が出る場合**:
   ```bash
   # hookファイルを確認
   head -n 30 /Users/harieshokunin/claude-context-manager/src/hooks/user-prompt-submit.py

   # stdin空チェックが入っているか確認（17-26行目付近）
   ```

2. **ログファイルが作成されない場合**:
   ```bash
   # ディレクトリのパーミッション確認
   ls -ld ~/.claude/context-history/
   ls -ld ~/.claude/context-history/.tmp/

   # 必要に応じて作成
   mkdir -p ~/.claude/context-history/.tmp/
   ```

3. **hook設定が重複している場合**:
   ```bash
   # グローバル設定を編集
   code ~/.claude/settings.json

   # "UserPromptSubmit", "PostToolUse", "Stop" をhooksセクションから削除
   ```

---

## 📝 チェックリスト完了後の報告

すべてのチェックが完了したら、以下を報告してください：

- [ ] Hook動作確認: ✅ 正常 / ❌ エラー
- [ ] ログファイル作成: ✅ 正常 / ❌ エラー
- [ ] エラーログ: ✅ エラーなし / ❌ エラーあり
- [ ] Hook設定: ✅ 正常（重複なし） / ❌ 重複あり
- [ ] テストスイート: ✅ 12個以上PASS / ❌ 失敗多数
- [ ] 実際のセッション: ✅ ログ記録される / ❌ 記録されない

---

**すべて ✅ なら、Claude Context Manager は正常に動作しています！**
