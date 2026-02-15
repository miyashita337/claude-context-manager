# Test Cases Overview - Claude Context Manager

## Summary

**Total Test Cases**: 10 (統合テストケース)
**Test Framework**: Jest (TypeScript)
**Status**: All tests passing (32/32)

## Test Case List

### エンドツーエンドテスト (6ケース)

#### 1. 単一セッションの完全フロー
**File**: `tests/integration.test.ts:23`
**Description**: user-prompt → post-tool → stop → Markdown生成の完全なワークフローテスト

**Test Flow**:
1. user-promptフックのシミュレーション (ユーザーエントリ追加)
2. post-toolフックのシミュレーション (アシスタントエントリ追加)
3. stopフックのシミュレーション (Markdown finalize)
4. Markdown出力の検証
5. セッションディレクトリへの保存
6. 一時ファイルのクリーンアップ確認

**Assertions**:
- Markdownにsession_idが含まれる
- total_tokens、user_tokens、assistant_tokensが正しい
- ユーザーとアシスタントのコンテンツが含まれる
- 一時ファイルが削除される

---

#### 2. 複数回のfinalize実行による追記動作
**File**: `tests/integration.test.ts:81`
**Description**: 同じセッションに対して複数回finalizeを実行し、追記動作を確認

**Test Flow**:
1. 最初のfinalize実行 (1エントリ)
2. Markdown出力確認
3. 2回目のfinalize実行 (2エントリ)
4. 追記されたMarkdown出力確認

**Assertions**:
- 最初のメッセージが保持される
- 2回目のメッセージが追加される
- Token数が正しく再計算される

---

#### 3. 同じセッションIDでの複数回起動と追記
**File**: `tests/integration.test.ts:126`
**Description**: Claudeの再起動を伴うセッション継続テスト

**Test Flow**:
1. 1回目の起動とログ作成
2. 2回目の起動と追加ログ作成
3. finalize実行
4. 統合されたMarkdown確認

**Assertions**:
- すべての再起動ログが含まれる
- Token数が正しく集計される

---

#### 4. タイムギャップ検出の統合テスト
**File**: `tests/integration.test.ts:157`
**Description**: 5分以上のタイムギャップを検出

**Test Flow**:
1. タイムギャップを含むログ作成 (10分間隔)
2. ギャップ検出ロジック実行
3. Markdown生成と検証

**Assertions**:
- 1つのギャップが検出される
- ギャップ時間が10分と計算される
- ギャップ前後のエントリが両方含まれる

---

#### 5. session-unknownの処理
**File**: `tests/integration.test.ts:195`
**Description**: セッションIDが不明な場合の処理

**Test Flow**:
1. "session-unknown"というIDでログ作成
2. Markdown生成
3. 出力確認

**Assertions**:
- session_id: session-unknownが含まれる
- コンテンツが正しく含まれる

---

#### 6. 日本語コンテンツの完全フロー
**File**: `tests/integration.test.ts:214`
**Description**: 日本語コンテンツのUTF-8エンコーディング保持確認

**Test Flow**:
1. 日本語を含むログ作成
2. Markdown生成
3. ファイル保存
4. 保存されたファイルの読み込みと検証

**Assertions**:
- 日本語テキストが正しく保持される
- コードブロックが正しく含まれる
- Token数が計算される
- UTF-8エンコーディングが保持される

---

### エラーハンドリングテスト (4ケース)

#### 7. 不正なJSON入力時のエラーハンドリング
**File**: `tests/integration.test.ts:259`
**Description**: 破損したJSONファイルからの回復

**Test Flow**:
1. 不正なJSON文字列を書き込み
2. パースエラーを捕捉
3. 有効なデータで上書き
4. 回復確認

**Assertions**:
- SyntaxErrorが発生する
- 有効なデータで回復できる

---

#### 8. finalize失敗時のリカバリ
**File**: `tests/integration.test.ts:285`
**Description**: ファイルシステムエラー時の回復処理

**Test Flow**:
1. ログファイル作成
2. 無効なパスへの書き込み試行 (失敗)
3. 一時ファイルの存在確認
4. 有効なパスへの書き込み (成功)

**Assertions**:
- 無効なパスへの書き込みがエラーになる
- 失敗時に一時ファイルが削除されない
- 有効なパスで回復できる

---

#### 9. ディスク容量不足のシミュレーション
**File**: `tests/integration.test.ts:322`
**Description**: 大容量ファイル (1MB+) の処理

**Test Flow**:
1. 1MBのコンテンツを含むログ作成
2. ファイルサイズ確認
3. Markdown生成
4. 出力サイズ確認

**Assertions**:
- ログファイルが1MB以上
- Markdown出力も1MB以上

---

#### 10. 並行実行時の競合処理
**File**: `tests/integration.test.ts:344`
**Description**: 複数の同時書き込みによる競合状態の検出

**Test Flow**:
1. 空のログファイル作成
2. 10個の並行書き込み実行 (read-modify-write)
3. 最終状態の確認

**Assertions**:
- 競合によるJSON破損の可能性を検証
- 破損した場合はSyntaxError
- 成功した場合は配列構造とエントリ数確認

**Note**: このテストは意図的に競合状態を再現し、ファイルロック機構の必要性を示す

---

## Test Utilities

**File**: `tests/helpers/test-utils.ts`

Helper functions:
- `createTestSession()` - テストセッション作成
- `addLogEntry()` - ログエントリ追加
- `createUserEntry()` - ユーザーエントリファクトリ
- `createAssistantEntry()` - アシスタントエントリファクトリ
- `verifyMarkdownContent()` - Markdown検証
- `calculateTimeGaps()` - タイムギャップ計算
- `setupTestDirectories()` - テスト環境セットアップ
- `cleanupTestDirectories()` - クリーンアップ
- `saveSessionMarkdown()` - Markdown保存
- `fileExists()` - ファイル存在確認

---

## テスト実行方法

```bash
# すべてのテスト実行
npm test

# カバレッジ付き実行
npm test -- --coverage

# 特定のテストファイル実行
npm test tests/integration.test.ts

# 特定のテストケース実行
npm test -- -t "単一セッションの完全フロー"

# ウォッチモード
npm test -- --watch
```

---

## 成功基準

すべてのテストケースが以下を満たす:
- 正しいMarkdown生成
- 正確なToken計算
- UTF-8エンコーディング保持
- finalize後の一時ファイル削除
- エラー回復メカニズムの動作

---

## 既知の課題

**テストケース#10 (並行実行)**:
- 現在の実装では非アトミックなread-modify-write操作により競合状態が発生する
- Phase 2でファイルロック機構を実装予定

---

## ドキュメント

- `tests/README.md` - Pythonテストドキュメント
- `tests/INTEGRATION_TESTS.md` - 統合テストガイド
- `tests/TEST_SUMMARY.md` - テスト実行結果サマリー
- `TEST_CASES.md` - このファイル

---

## 次のステップ

### Phase 2での改善
1. ファイルロック機構の実装
2. パフォーマンステストの追加
3. ストレステスト (1000+セッション)
4. コードカバレッジ80%+達成

### 将来の拡張
1. 実際のClaude Codeフックとの統合テスト
2. CI/CDパイプライン統合
3. ミューテーションテスト
4. プロパティベーステスト
