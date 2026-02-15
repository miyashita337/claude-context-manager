# 🚀 新セッション起動時クイックチェック

以下をコピーして、Claudeに貼り付けてください：

---

## Claude Context Manager の動作確認をお願いします

以下のチェックを順番に実行して、結果を報告してください：

### 1. Hook動作テスト
```bash
# 正常なJSON入力テスト
echo '{"session_id": "startup-check", "prompt": "起動確認"}' | python3 /Users/harieshokunin/claude-context-manager/src/hooks/user-prompt-submit.py

# 空stdin テスト
echo '' | python3 /Users/harieshokunin/claude-context-manager/src/hooks/user-prompt-submit.py
```

**期待される結果**:
- 1つ目: `{"hookSpecificOutput": {"status": "logged", ...}}`
- 2つ目: `{"hookSpecificOutput": {"status": "skipped", "reason": "empty stdin"}}`

---

### 2. エラーログ確認
```bash
tail -n 30 ~/.claude/hook-debug.log 2>/dev/null || echo "エラーログなし（正常）"
```

**期待される結果**:
- `JSONDecodeError` や `stdin is empty` エラーが**出ていない**こと

---

### 3. ログファイル作成確認
```bash
ls -la ~/.claude/context-history/.tmp/session-startup-check.json
cat ~/.claude/context-history/.tmp/session-startup-check.json
```

**期待される結果**:
- ファイルが存在し、JSON Lines形式でログが記録されていること

---

### 4. Hook設定の重複確認
```bash
cat ~/.claude/settings.json | python3 -m json.tool | grep -A 5 '"UserPromptSubmit"'
```

**期待される結果**:
- グローバル設定に `UserPromptSubmit` が**存在しない**こと（重複解消済み）

---

### 5. テスト実行（オプション）
```bash
cd /Users/harieshokunin/claude-context-manager && python3 -m pytest tests/test_hooks.py::test_stdin_empty_handling tests/test_hooks.py::test_stdin_whitespace_only_handling -v
```

**期待される結果**:
- 2つのテストが両方とも PASSED

---

## 報告フォーマット

すべてのチェックを実行したら、以下の形式で報告してください：

```
【チェック結果】
1. Hook動作テスト: ✅ / ❌
2. エラーログ: ✅ エラーなし / ❌ エラーあり
3. ログファイル作成: ✅ / ❌
4. Hook設定重複: ✅ 重複なし / ❌ 重複あり
5. テスト実行: ✅ PASSED / ❌ FAILED

【問題があれば】
- エラーメッセージや異常な出力を記載
```

---

**すべて ✅ なら正常に動作しています！**
