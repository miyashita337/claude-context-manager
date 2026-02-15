/**
 * Test cases for MarkdownWriter
 */

import { MarkdownWriter } from '../src/core/markdown-writer.js';
import type { LogEntry } from '../src/types/session.js';

describe('MarkdownWriter', () => {
  let writer: MarkdownWriter;

  beforeEach(() => {
    writer = new MarkdownWriter();
  });

  describe('基本的なMarkdown生成', () => {
    test('ケース1: 新規Markdown生成（基本）- 単一エントリ', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'こんにちは',
          tokens_estimate: 10,
        },
      ];

      const markdown = await writer.generate('test-session-1', logs);

      // Frontmatterの検証
      expect(markdown).toContain('---');
      expect(markdown).toContain('date: 2026-02-12T10:00:00.000Z');
      expect(markdown).toContain('session_id: test-session-1');
      expect(markdown).toContain('total_tokens: 10');
      expect(markdown).toContain('user_tokens: 10');
      expect(markdown).toContain('assistant_tokens: 0');
      expect(markdown).toContain('compact_detected: false');

      // ヘッダーの検証
      expect(markdown).toContain('# Claude対話履歴 - 2026-02-12');

      // コンテンツの検証
      expect(markdown).toContain('ユーザー');
      expect(markdown).toContain('こんにちは');
      expect(markdown).toContain('**Tokens**: 10');

      // 統計の検証
      expect(markdown).toContain('**セッション統計**');
      expect(markdown).toContain('総Token数: 10');
      expect(markdown).toContain('エントリ数: 1');
    });

    test('ケース2: 複数エントリの生成（ユーザーとアシスタント）', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'TypeScriptについて教えて',
          tokens_estimate: 20,
        },
        {
          timestamp: '2026-02-12T10:01:00.000Z',
          type: 'assistant',
          content: 'TypeScriptは型安全なJavaScriptのスーパーセットです。',
          tokens_estimate: 30,
        },
        {
          timestamp: '2026-02-12T10:02:00.000Z',
          type: 'user',
          content: 'もっと詳しく教えて',
          tokens_estimate: 15,
        },
      ];

      const markdown = await writer.generate('test-session-2', logs);

      // Token計算の検証
      expect(markdown).toContain('total_tokens: 65');
      expect(markdown).toContain('user_tokens: 35');
      expect(markdown).toContain('assistant_tokens: 30');

      // 全エントリが含まれているか
      expect(markdown).toContain('TypeScriptについて教えて');
      expect(markdown).toContain('TypeScriptは型安全なJavaScriptのスーパーセットです。');
      expect(markdown).toContain('もっと詳しく教えて');

      // エントリ数の検証
      expect(markdown).toContain('エントリ数: 3');
    });

    test('ケース3: ツール名付きアシスタントエントリ', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'ファイルを読み込んで',
          tokens_estimate: 20,
        },
        {
          timestamp: '2026-02-12T10:01:00.000Z',
          type: 'assistant',
          content: 'ファイルを読み込みます',
          tokens_estimate: 25,
          tool_name: 'Read',
          tool_input: { file_path: '/test/file.txt' },
        },
      ];

      const markdown = await writer.generate('test-session-3', logs);

      // ツール名が表示されているか
      expect(markdown).toContain('Claude (Read)');
      expect(markdown).toContain('ファイルを読み込みます');
    });
  });

  describe('タイムギャップ検出', () => {
    test('ケース4: タイムギャップなし（連続したエントリ）', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: '最初のメッセージ',
          tokens_estimate: 20,
        },
        {
          timestamp: '2026-02-12T10:05:00.000Z',
          type: 'assistant',
          content: '5分後の返信',
          tokens_estimate: 25,
        },
        {
          timestamp: '2026-02-12T10:10:00.000Z',
          type: 'user',
          content: '10分後のメッセージ',
          tokens_estimate: 20,
        },
      ];

      const markdown = await writer.generate('test-session-4', logs);

      // 時間が正しく計算されているか（10分）
      expect(markdown).toContain('セッション時間: 10分');

      // 全てのエントリが含まれているか
      expect(markdown).toContain('最初のメッセージ');
      expect(markdown).toContain('5分後の返信');
      expect(markdown).toContain('10分後のメッセージ');
    });

    test('ケース5: タイムギャップ検出（30分以上の間隔）', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: '最初のメッセージ',
          tokens_estimate: 20,
        },
        {
          timestamp: '2026-02-12T10:35:00.000Z',
          type: 'user',
          content: '35分後のメッセージ',
          tokens_estimate: 20,
        },
      ];

      const markdown = await writer.generate('test-session-5', logs);

      // 時間が正しく計算されているか（35分）
      expect(markdown).toContain('セッション時間: 35分');

      // 両方のエントリが含まれているか
      expect(markdown).toContain('最初のメッセージ');
      expect(markdown).toContain('35分後のメッセージ');
    });
  });

  describe('統計計算の正確性', () => {
    test('ケース6: Token統計の正確な計算', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'メッセージ1',
          tokens_estimate: 100,
        },
        {
          timestamp: '2026-02-12T10:01:00.000Z',
          type: 'assistant',
          content: '返信1',
          tokens_estimate: 150,
        },
        {
          timestamp: '2026-02-12T10:02:00.000Z',
          type: 'user',
          content: 'メッセージ2',
          tokens_estimate: 200,
        },
        {
          timestamp: '2026-02-12T10:03:00.000Z',
          type: 'assistant',
          content: '返信2',
          tokens_estimate: 250,
        },
      ];

      const markdown = await writer.generate('test-session-6', logs);

      // Token統計の検証
      expect(markdown).toContain('total_tokens: 700');
      expect(markdown).toContain('user_tokens: 300');
      expect(markdown).toContain('assistant_tokens: 400');
      expect(markdown).toContain('総Token数: 700');
      expect(markdown).toContain('ユーザーToken: 300');
      expect(markdown).toContain('ClaudeToken: 400');

      // 時間とエントリ数
      expect(markdown).toContain('セッション時間: 3分');
      expect(markdown).toContain('エントリ数: 4');
    });

    test('ケース7: tokens_estimateが0のエントリ', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: '空のメッセージ',
          tokens_estimate: 0,
        },
        {
          timestamp: '2026-02-12T10:01:00.000Z',
          type: 'assistant',
          content: '通常のメッセージ',
          tokens_estimate: 50,
        },
      ];

      const markdown = await writer.generate('test-session-7', logs);

      expect(markdown).toContain('total_tokens: 50');
      expect(markdown).toContain('user_tokens: 0');
      expect(markdown).toContain('assistant_tokens: 50');
    });
  });

  describe('エラーハンドリング', () => {
    test('ケース8: 空の配列でエラーを投げる', async () => {
      const logs: LogEntry[] = [];

      await expect(writer.generate('test-session-8', logs)).rejects.toThrow(
        'No logs to generate markdown from'
      );
    });

    test('ケース9: タイムスタンプが不正な場合', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: 'invalid-timestamp',
          type: 'user',
          content: 'メッセージ',
          tokens_estimate: 10,
        },
      ];

      // Invalid Dateの場合、toISOString()がRangeErrorを投げることを期待
      await expect(
        writer.generate('test-session-9', logs)
      ).rejects.toThrow(RangeError);
    });

    test('ケース10: tool_nameがundefinedの場合', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'assistant',
          content: 'ツールなしのアシスタント',
          tokens_estimate: 20,
          tool_name: undefined,
        },
      ];

      const markdown = await writer.generate('test-session-10', logs);

      // tool_nameがない場合は "Claude" のみ表示
      expect(markdown).toContain('## ');
      expect(markdown).toContain('Claude');
      expect(markdown).not.toContain('Claude ()');
    });
  });

  describe('日本語フォーマット', () => {
    test('ケース11: 日本語のタイムフォーマット', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T15:30:45.000Z',
          type: 'user',
          content: 'テスト',
          tokens_estimate: 10,
        },
      ];

      const markdown = await writer.generate('test-session-11', logs);

      // 日本語の時刻表示を含むか（環境によって変わる可能性があるため、時刻が含まれていることのみ確認）
      expect(markdown).toMatch(/##\s+\d+:\d+:\d+\s+-\s+ユーザー/);
    });

    test('ケース12: 日本語のラベル表示', async () => {
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'テスト',
          tokens_estimate: 10,
        },
      ];

      const markdown = await writer.generate('test-session-12', logs);

      // 日本語のラベルが含まれているか
      expect(markdown).toContain('ユーザー');
      expect(markdown).toContain('Claude対話履歴');
      expect(markdown).toContain('セッション統計');
      expect(markdown).toContain('総Token数');
      expect(markdown).toContain('ユーザーToken');
      expect(markdown).toContain('ClaudeToken');
      expect(markdown).toContain('Compact: なし');
      expect(markdown).toContain('セッション時間');
      expect(markdown).toContain('エントリ数');
    });
  });
});
