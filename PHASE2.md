# Claude Context Manager - Phase 2 実装計画（SOW）

**作成日**: 2026-02-12
**対象バージョン**: v0.2.0
**前提条件**: Phase 1 MVP完了

---

## Phase 2 目標

Phase 1で実装した基本機能を拡張し、以下を実現する：

1. **完全なCLI実装** - status, search以外のコマンド
2. **正確なToken計測** - tiktoken完全統合
3. **ログローテーション** - 自動アーカイブ機能
4. **Export機能拡張** - Zenn, JSON, PDF対応
5. **Compact検出** - ヒューリスティック検出
6. **SQLite統合** - 高速検索インデックス

---

## 実装スケジュール（Week 9-16）

### Week 9-10: CLI完全実装

#### 1. export コマンド実装

**ファイル**: `src/cli/commands/export.ts`

**機能**:
- Obsidian形式（既存）
- Zenn形式（新規）
  - Frontmatterを`---`から`---\ntitle: ...\n---`形式に変換
  - コードブロックの調整
  - 画像パスの変換
- JSON形式（新規）
  - 構造化データとしてExport
  - APIとの連携用
- PDF形式（オプション）
  - markdown-pdfまたはpuppeteerを使用

**実装例**:
```typescript
// src/cli/commands/export.ts
import { Command } from 'commander';
import * as fs from 'fs/promises';
import * as path from 'path';

export function registerExportCommand(program: Command) {
  program
    .command('export')
    .description('Export session to different formats')
    .argument('<session-id>', 'Session ID to export')
    .option('-f, --format <format>', 'Export format (obsidian|zenn|json|pdf)', 'obsidian')
    .option('-o, --output <path>', 'Output file path')
    .action(async (sessionId, options) => {
      // Implementation
    });
}
```

**検証**:
```bash
# Zenn形式でExport
npx tsx src/cli/index.ts export session-abc123 --format zenn -o ~/Desktop/article.md

# JSON形式でExport
npx tsx src/cli/index.ts export session-abc123 --format json -o output.json
```

---

#### 2. rotate コマンド実装

**ファイル**:
- `src/cli/commands/rotate.ts`
- `src/core/rotation-manager.ts`（既存プランから）

**機能**:
- 指定日数以前のセッションをアーカイブ
- tar.gz形式で圧縮
- アーカイブ後に元ファイルを削除
- cron設定の案内

**実装例**:
```typescript
// src/core/rotation-manager.ts
export class RotationManager {
  async rotate(days: number = 30): Promise<void> {
    const sessionsDir = path.join(
      process.env.HOME!,
      '.claude',
      'context-history',
      'sessions'
    );
    const archivesDir = path.join(
      process.env.HOME!,
      '.claude',
      'context-history',
      'archives'
    );

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    const dateDirs = await fs.readdir(sessionsDir);

    for (const dateDir of dateDirs) {
      const date = new Date(dateDir);
      if (date < cutoffDate) {
        // tar.gz作成
        await this.archiveDirectory(dateDir, sessionsDir, archivesDir);
      }
    }
  }
}
```

**検証**:
```bash
# 30日以前のログをアーカイブ
npx tsx src/cli/index.ts rotate --days 30

# アーカイブ確認
ls ~/.claude/context-history/archives/
```

---

#### 3. config コマンド実装

**ファイル**: `src/cli/commands/config.ts`

**機能**:
- Token計測方法の切り替え（heuristic/tiktoken）
- アーカイブ設定（自動ローテーション日数）
- Export設定（デフォルトフォーマット）

**実装例**:
```typescript
// src/cli/commands/config.ts
export async function configCommand(key?: string, value?: string) {
  const configFile = path.join(
    process.env.HOME!,
    '.claude',
    'context-history',
    '.metadata',
    'config.json'
  );

  if (!key) {
    // 全設定を表示
    const config = await loadConfig(configFile);
    console.table(config);
    return;
  }

  if (!value) {
    // 特定の設定値を表示
    const config = await loadConfig(configFile);
    console.log(`${key}: ${config[key]}`);
    return;
  }

  // 設定を更新
  await updateConfig(configFile, key, value);
  console.log(`✓ ${key} set to ${value}`);
}
```

**検証**:
```bash
# 設定確認
npx tsx src/cli/index.ts config

# Token計測方法を変更
npx tsx src/cli/index.ts config tokenizer tiktoken

# 自動ローテーション日数を設定
npx tsx src/cli/index.ts config rotation_days 60
```

---

### Week 11-12: Token計測の正確化

#### 1. tiktoken完全統合

**ファイル**: `src/core/tokenizer.ts`（既存を拡張）

**変更内容**:
- 現在の`p50k_base`を維持しつつ、Claude 3.5用のエンコーダを追加
- Anthropic公式tokenizer APIの統合（オプション）
- 設定ファイルで計測方法を切り替え可能に

**実装例**:
```typescript
// src/core/tokenizer.ts
import { Tiktoken, get_encoding } from 'tiktoken';

type TokenizerMode = 'heuristic' | 'tiktoken' | 'anthropic';

export class Tokenizer {
  private mode: TokenizerMode;
  private encoder: Tiktoken | null = null;

  constructor(mode: TokenizerMode = 'tiktoken') {
    this.mode = mode;
  }

  async estimateTokens(text: string): Promise<number> {
    switch (this.mode) {
      case 'heuristic':
        return Math.ceil(text.length / 4);

      case 'tiktoken':
        if (!this.encoder) {
          this.encoder = get_encoding('p50k_base');
        }
        return this.encoder.encode(text).length;

      case 'anthropic':
        // Anthropic API呼び出し（要API key）
        return await this.callAnthropicTokenizer(text);

      default:
        throw new Error(`Unknown tokenizer mode: ${this.mode}`);
    }
  }

  private async callAnthropicTokenizer(text: string): Promise<number> {
    // client.messages.countTokens() を使用
    // 詳細はAnthropic APIドキュメント参照
    throw new Error('Not implemented yet');
  }
}
```

**検証**:
```bash
# 既存セッションのToken数を再計算
npx tsx src/cli/index.ts recalculate --tokenizer tiktoken
```

---

#### 2. Token計測の精度比較ツール

**ファイル**: `src/cli/commands/compare-tokens.ts`

**機能**:
- heuristic vs tiktoken vs Anthropic APIの比較
- 既存セッションに対して3つの方法でToken数を計算
- 差異レポートを出力

**実装例**:
```typescript
export async function compareTokensCommand(sessionId: string) {
  const sessionFile = await findSessionFile(sessionId);
  const logs = await loadSessionLogs(sessionFile);

  const results = {
    heuristic: 0,
    tiktoken: 0,
    anthropic: 0,
  };

  for (const log of logs) {
    results.heuristic += estimateTokensHeuristic(log.content);
    results.tiktoken += estimateTokensTiktoken(log.content);
    // results.anthropic += await estimateTokensAnthropic(log.content);
  }

  console.table(results);

  const diff = Math.abs(results.tiktoken - results.heuristic);
  const accuracy = (1 - diff / results.tiktoken) * 100;
  console.log(`Heuristic accuracy: ${accuracy.toFixed(2)}%`);
}
```

---

### Week 13-14: Compact検出とSQLite統合

#### 1. Compact検出（ヒューリスティック）

**ファイル**: `src/core/compact-detector.ts`

**検出ロジック**:
- Token数の急激な減少を検出（50%以上の減少）
- タイムスタンプの不連続を検出
- メッセージ数の減少を検出

**実装例**:
```typescript
// src/core/compact-detector.ts
export class CompactDetector {
  detectCompact(logs: LogEntry[]): CompactEvent[] {
    const compactEvents: CompactEvent[] = [];

    for (let i = 1; i < logs.length; i++) {
      const prev = logs[i - 1];
      const curr = logs[i];

      // Token数の急激な減少
      const tokenDrop = prev.tokens_estimate - curr.tokens_estimate;
      const dropRatio = tokenDrop / prev.tokens_estimate;

      if (dropRatio > 0.5) {
        compactEvents.push({
          timestamp: curr.timestamp,
          type: 'token_drop',
          severity: 'high',
          details: {
            before: prev.tokens_estimate,
            after: curr.tokens_estimate,
            drop: tokenDrop,
            ratio: dropRatio,
          },
        });
      }

      // タイムスタンプの不連続（5分以上の間隔）
      const timeDiff = new Date(curr.timestamp).getTime() -
                       new Date(prev.timestamp).getTime();
      if (timeDiff > 300000) { // 5分
        compactEvents.push({
          timestamp: curr.timestamp,
          type: 'time_gap',
          severity: 'medium',
          details: {
            gap_ms: timeDiff,
            gap_minutes: timeDiff / 60000,
          },
        });
      }
    }

    return compactEvents;
  }
}
```

**検証**:
```bash
# Compact検出レポート
npx tsx src/cli/index.ts detect-compact session-abc123
```

---

#### 2. SQLite統合（検索インデックス）

**ファイル**:
- `src/core/database.ts`
- `src/core/indexer.ts`

**テーブル設計**:
```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT,
  total_tokens INTEGER,
  user_tokens INTEGER,
  assistant_tokens INTEGER,
  entry_count INTEGER,
  compact_detected BOOLEAN DEFAULT 0,
  file_path TEXT NOT NULL
);

CREATE TABLE entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  type TEXT NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  tokens_estimate INTEGER,
  tool_name TEXT,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_sessions_date ON sessions(date);
CREATE INDEX idx_entries_session ON entries(session_id);
CREATE INDEX idx_entries_content ON entries(content); -- FTS5に移行予定
```

**実装例**:
```typescript
// src/core/database.ts
import Database from 'better-sqlite3';

export class SessionDatabase {
  private db: Database.Database;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.initSchema();
  }

  private initSchema() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        total_tokens INTEGER,
        user_tokens INTEGER,
        assistant_tokens INTEGER,
        entry_count INTEGER,
        compact_detected BOOLEAN DEFAULT 0,
        file_path TEXT NOT NULL
      );
      -- 他のテーブルとインデックス...
    `);
  }

  insertSession(session: SessionMetadata): void {
    const stmt = this.db.prepare(`
      INSERT INTO sessions (id, date, start_time, end_time, total_tokens,
                           user_tokens, assistant_tokens, entry_count,
                           compact_detected, file_path)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    stmt.run(
      session.session_id,
      session.date,
      session.start_time,
      session.end_time,
      session.total_tokens,
      session.user_tokens,
      session.assistant_tokens,
      session.entry_count,
      session.compact_detected ? 1 : 0,
      session.file_path
    );
  }

  searchSessions(query: string, filters: SearchFilters): SessionMetadata[] {
    // 検索実装
  }
}
```

**検証**:
```bash
# 既存セッションをインデックス化
npx tsx src/cli/index.ts index --rebuild

# SQLiteベースの検索
npx tsx src/cli/index.ts search "TypeScript" --use-db
```

---

### Week 15-16: Export拡張とドキュメント

#### 1. Zenn形式Export実装

**ファイル**: `src/formatters/zenn-formatter.ts`

**変換ロジック**:
- Frontmatterを`---\ntitle: ...\ntopics: [...]\npublished: false\n---`形式に
- コードブロックをZenn記法に調整
- 見出しレベルを調整（H1 → H2）

**実装例**:
```typescript
// src/formatters/zenn-formatter.ts
export class ZennFormatter {
  format(sessionId: string, logs: LogEntry[]): string {
    const title = this.generateTitle(logs);
    const topics = this.extractTopics(logs);

    let markdown = `---
title: "${title}"
emoji: "💬"
type: "tech"
topics: [${topics.map(t => `"${t}"`).join(', ')}]
published: false
---

`;

    // 本文を生成
    for (const log of logs) {
      if (log.type === 'user') {
        markdown += `## 質問\n\n${log.content}\n\n`;
      } else {
        markdown += `## 回答\n\n${log.content}\n\n`;
      }
    }

    return markdown;
  }

  private generateTitle(logs: LogEntry[]): string {
    // 最初のユーザーメッセージから自動生成
    const firstUser = logs.find(l => l.type === 'user');
    if (!firstUser) return 'Untitled';

    const firstLine = firstUser.content.split('\n')[0];
    return firstLine.substring(0, 50);
  }

  private extractTopics(logs: LogEntry[]): string[] {
    // キーワード抽出（簡易版）
    // Phase 3でLLM活用予定
    return ['claude', 'ai'];
  }
}
```

---

#### 2. ドキュメント更新

**更新対象**:
- `README.md` - Phase 2完了に伴う更新
- `CHANGELOG.md` - 新規作成
- `CONTRIBUTING.md` - 新規作成

**CHANGELOG.md例**:
```markdown
# Changelog

## [0.2.0] - 2026-XX-XX

### Added
- Export command with Zenn/JSON/PDF support
- Log rotation with automatic archiving
- Config command for settings management
- Tiktoken full integration for accurate token counting
- Compact detection (heuristic-based)
- SQLite integration for fast search
- Compare-tokens command for accuracy measurement

### Changed
- Improved search command with database backend
- Enhanced status command with compact warnings

### Fixed
- Token estimation accuracy improved from ~70% to ~95%

## [0.1.0] - 2026-02-12

### Added
- Initial release (Phase 1 MVP)
- Hook-based capture system
- Markdown export with Obsidian compatibility
- Status and search CLI commands
- Token estimation (heuristic)
```

---

## Phase 2 完了基準

### 機能要件
- [x] export コマンド（Zenn, JSON対応）
- [x] rotate コマンド（自動アーカイブ）
- [x] config コマンド（設定管理）
- [x] tiktoken完全統合
- [x] Compact検出
- [x] SQLite統合

### 非機能要件
- Token計測精度: 90%以上
- 検索速度: 1000セッション対象で1秒以内
- アーカイブ圧縮率: 70%以上

### ドキュメント
- [x] README.md更新
- [x] CHANGELOG.md作成
- [x] API documentation（JSDoc）

---

## Phase 3への移行（参考）

Phase 3では以下を実装予定：

1. **Web Dashboard**
   - React + Next.js
   - Token使用量の可視化グラフ
   - セッション一覧・詳細表示
   - リアルタイム検索

2. **LLM連携**
   - 自動要約生成
   - トピック自動抽出
   - 類似セッション検索

3. **チーム機能**
   - セッション共有
   - コメント機能
   - アクセス制御

---

## リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| SQLite性能不足 | 検索速度低下 | FTS5（Full-Text Search）の活用、インデックス最適化 |
| tiktoken精度問題 | Token数のずれ | Anthropic公式APIとの比較検証を実施 |
| Compact検出の誤検知 | 誤報が多い | 閾値の調整、機械学習による改善（Phase 3） |
| Export形式の互換性 | Zennで表示崩れ | Zenn CLIでの検証を徹底 |

---

## 次回セッションでの開始手順

```bash
# 1. プロジェクトディレクトリに移動
cd /Users/harieshokunin/claude-context-manager

# 2. Phase 2ブランチ作成（オプション）
git checkout -b phase2

# 3. 依存関係追加
npm install better-sqlite3 @types/better-sqlite3

# 4. Week 9-10から実装開始
# まず export コマンドから実装
```

---

**Phase 2 実装完了予定**: 2026年3月末
**Phase 3 開始予定**: 2026年4月
