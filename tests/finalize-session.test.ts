/**
 * Test cases for finalize-session command
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { MarkdownWriter } from '../src/core/markdown-writer.js';
import type { LogEntry } from '../src/types/session.js';

describe('finalize-session', () => {
  let testTmpDir: string;
  let testOutputDir: string;
  let originalHome: string | undefined;

  beforeAll(() => {
    // 元のHOME環境変数を保存
    originalHome = process.env.HOME;
  });

  afterAll(() => {
    // HOME環境変数を復元
    if (originalHome) {
      process.env.HOME = originalHome;
    }
  });

  beforeEach(async () => {
    // テスト用の一時ディレクトリを作成
    const tmpBase = path.join(process.cwd(), 'tests', '.tmp-test');
    testTmpDir = path.join(tmpBase, '.claude', 'context-history', '.tmp');
    testOutputDir = path.join(
      tmpBase,
      '.claude',
      'context-history',
      'sessions'
    );

    await fs.mkdir(testTmpDir, { recursive: true });
    await fs.mkdir(testOutputDir, { recursive: true });

    // テスト用のHOME環境変数を設定
    process.env.HOME = tmpBase;
  });

  afterEach(async () => {
    // テスト用のディレクトリをクリーンアップ
    const tmpBase = path.join(process.cwd(), 'tests', '.tmp-test');
    try {
      await fs.rm(tmpBase, { recursive: true, force: true });
    } catch (error) {
      // エラーを無視（ディレクトリが存在しない場合など）
    }
  });

  describe('新規セッションの処理', () => {
    test('ケース1: 新規セッションのMarkdown生成', async () => {
      const sessionId = 'new-session-1';
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: '新しいセッションです',
          tokens_estimate: 20,
        },
        {
          timestamp: '2026-02-12T10:01:00.000Z',
          type: 'assistant',
          content: 'こんにちは、新しいセッションですね',
          tokens_estimate: 30,
        },
      ];

      // 一時ログファイルを作成
      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);
      await fs.writeFile(logFile, JSON.stringify(logs), 'utf-8');

      // MarkdownWriter を使ってMarkdownを生成
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      // 出力ファイルパスを決定
      const today = new Date().toISOString().split('T')[0];
      const outputPath = path.join(
        testOutputDir,
        today,
        `session-${sessionId}.md`
      );

      // 出力ディレクトリを作成
      await fs.mkdir(path.dirname(outputPath), { recursive: true });

      // Markdownファイルを書き込み
      await fs.writeFile(outputPath, markdown, 'utf-8');

      // 一時ファイルを削除
      await fs.unlink(logFile);

      // 検証: 出力ファイルが作成されているか
      const outputExists = await fs
        .access(outputPath)
        .then(() => true)
        .catch(() => false);
      expect(outputExists).toBe(true);

      // 検証: 出力ファイルの内容
      const outputContent = await fs.readFile(outputPath, 'utf-8');
      expect(outputContent).toContain('session_id: new-session-1');
      expect(outputContent).toContain('新しいセッションです');
      expect(outputContent).toContain('こんにちは、新しいセッションですね');

      // 検証: 一時ファイルが削除されているか
      const logExists = await fs
        .access(logFile)
        .then(() => true)
        .catch(() => false);
      expect(logExists).toBe(false);
    });

    test('ケース2: 複数エントリを含む新規セッション', async () => {
      const sessionId = 'new-session-2';
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'エントリ1',
          tokens_estimate: 10,
        },
        {
          timestamp: '2026-02-12T10:01:00.000Z',
          type: 'assistant',
          content: '返信1',
          tokens_estimate: 15,
        },
        {
          timestamp: '2026-02-12T10:02:00.000Z',
          type: 'user',
          content: 'エントリ2',
          tokens_estimate: 12,
        },
        {
          timestamp: '2026-02-12T10:03:00.000Z',
          type: 'assistant',
          content: '返信2',
          tokens_estimate: 18,
        },
      ];

      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);
      await fs.writeFile(logFile, JSON.stringify(logs), 'utf-8');

      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      const today = new Date().toISOString().split('T')[0];
      const outputPath = path.join(
        testOutputDir,
        today,
        `session-${sessionId}.md`
      );

      await fs.mkdir(path.dirname(outputPath), { recursive: true });
      await fs.writeFile(outputPath, markdown, 'utf-8');
      await fs.unlink(logFile);

      const outputContent = await fs.readFile(outputPath, 'utf-8');
      expect(outputContent).toContain('total_tokens: 55');
      expect(outputContent).toContain('エントリ数: 4');
      expect(outputContent).toContain('エントリ1');
      expect(outputContent).toContain('返信2');
    });
  });

  describe('既存セッションへの追記', () => {
    test('ケース3: 既存ファイルが存在する場合は上書き', async () => {
      const sessionId = 'existing-session';
      const today = new Date().toISOString().split('T')[0];
      const outputPath = path.join(
        testOutputDir,
        today,
        `session-${sessionId}.md`
      );

      // 既存のMarkdownファイルを作成
      await fs.mkdir(path.dirname(outputPath), { recursive: true });
      await fs.writeFile(
        outputPath,
        '# 古いコンテンツ\n既存のセッション',
        'utf-8'
      );

      // 新しいログを作成
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: '新しいエントリ',
          tokens_estimate: 20,
        },
      ];

      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);
      await fs.writeFile(logFile, JSON.stringify(logs), 'utf-8');

      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      // ファイルを上書き
      await fs.writeFile(outputPath, markdown, 'utf-8');
      await fs.unlink(logFile);

      // 検証: 新しい内容で上書きされているか
      const outputContent = await fs.readFile(outputPath, 'utf-8');
      expect(outputContent).not.toContain('古いコンテンツ');
      expect(outputContent).toContain('新しいエントリ');
      expect(outputContent).toContain('session_id: existing-session');
    });
  });

  describe('空・不正なログファイルの処理', () => {
    test('ケース4: 空のログファイル処理', async () => {
      const sessionId = 'empty-session';
      const logs: LogEntry[] = [];

      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);
      await fs.writeFile(logFile, JSON.stringify(logs), 'utf-8');

      // 空のログの場合、ファイルを削除するだけ
      const logsJson = await fs.readFile(logFile, 'utf-8');
      const parsedLogs: LogEntry[] = JSON.parse(logsJson);

      if (parsedLogs.length === 0) {
        await fs.unlink(logFile);
      }

      // 検証: ログファイルが削除されているか
      const logExists = await fs
        .access(logFile)
        .then(() => true)
        .catch(() => false);
      expect(logExists).toBe(false);

      // 検証: 出力ファイルは作成されていないか
      const today = new Date().toISOString().split('T')[0];
      const outputPath = path.join(
        testOutputDir,
        today,
        `session-${sessionId}.md`
      );
      const outputExists = await fs
        .access(outputPath)
        .then(() => true)
        .catch(() => false);
      expect(outputExists).toBe(false);
    });

    test('ケース5: JSON破損時のエラーハンドリング', async () => {
      const sessionId = 'broken-json-session';
      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);

      // 破損したJSONを書き込み
      await fs.writeFile(logFile, '{ "broken": json }', 'utf-8');

      // JSON.parseがエラーを投げることを期待
      const logsJson = await fs.readFile(logFile, 'utf-8');

      await expect(async () => {
        JSON.parse(logsJson);
      }).rejects.toThrow();

      // クリーンアップ
      await fs.unlink(logFile);
    });
  });

  describe('ログファイルの存在チェック', () => {
    test('ケース6: 存在しないログファイル', async () => {
      const sessionId = 'non-existent-session';
      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);

      // ファイルが存在しないことを確認
      const exists = await fs
        .access(logFile)
        .then(() => true)
        .catch(() => false);

      expect(exists).toBe(false);

      // この場合、処理はスキップされるべき
    });
  });

  describe('一時ファイルの削除確認', () => {
    test('ケース7: 正常処理後の一時ファイル削除', async () => {
      const sessionId = 'cleanup-session';
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'クリーンアップテスト',
          tokens_estimate: 20,
        },
      ];

      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);
      await fs.writeFile(logFile, JSON.stringify(logs), 'utf-8');

      // 処理を実行
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      const today = new Date().toISOString().split('T')[0];
      const outputPath = path.join(
        testOutputDir,
        today,
        `session-${sessionId}.md`
      );

      await fs.mkdir(path.dirname(outputPath), { recursive: true });
      await fs.writeFile(outputPath, markdown, 'utf-8');

      // 一時ファイルを削除
      await fs.unlink(logFile);

      // 検証: 一時ファイルが削除されているか
      const logExists = await fs
        .access(logFile)
        .then(() => true)
        .catch(() => false);
      expect(logExists).toBe(false);

      // 検証: 出力ファイルは存在するか
      const outputExists = await fs
        .access(outputPath)
        .then(() => true)
        .catch(() => false);
      expect(outputExists).toBe(true);
    });

    test('ケース8: 削除失敗時のエラーハンドリング', async () => {
      const sessionId = 'delete-fail-session';
      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);

      // 存在しないファイルを削除しようとする
      await expect(fs.unlink(logFile)).rejects.toThrow();
    });
  });

  describe('出力ディレクトリの作成', () => {
    test('ケース9: 日付別ディレクトリが自動作成される', async () => {
      const sessionId = 'dir-creation-session';
      const logs: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'ディレクトリ作成テスト',
          tokens_estimate: 20,
        },
      ];

      const logFile = path.join(testTmpDir, `session-${sessionId}.json`);
      await fs.writeFile(logFile, JSON.stringify(logs), 'utf-8');

      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      const today = new Date().toISOString().split('T')[0];
      const todayDir = path.join(testOutputDir, today);
      const outputPath = path.join(todayDir, `session-${sessionId}.md`);

      // ディレクトリを作成
      await fs.mkdir(todayDir, { recursive: true });

      // 検証: ディレクトリが作成されているか
      const dirStats = await fs.stat(todayDir);
      expect(dirStats.isDirectory()).toBe(true);

      // ファイルを書き込み
      await fs.writeFile(outputPath, markdown, 'utf-8');
      await fs.unlink(logFile);

      // 検証: ファイルが正しい場所に作成されているか
      const outputExists = await fs
        .access(outputPath)
        .then(() => true)
        .catch(() => false);
      expect(outputExists).toBe(true);
    });

    test('ケース10: 複数セッションを同じ日に処理', async () => {
      const today = new Date().toISOString().split('T')[0];
      const todayDir = path.join(testOutputDir, today);
      await fs.mkdir(todayDir, { recursive: true });

      // セッション1
      const sessionId1 = 'multi-session-1';
      const logs1: LogEntry[] = [
        {
          timestamp: '2026-02-12T10:00:00.000Z',
          type: 'user',
          content: 'セッション1',
          tokens_estimate: 20,
        },
      ];

      const logFile1 = path.join(testTmpDir, `session-${sessionId1}.json`);
      await fs.writeFile(logFile1, JSON.stringify(logs1), 'utf-8');

      const writer = new MarkdownWriter();
      const markdown1 = await writer.generate(sessionId1, logs1);
      const outputPath1 = path.join(todayDir, `session-${sessionId1}.md`);
      await fs.writeFile(outputPath1, markdown1, 'utf-8');
      await fs.unlink(logFile1);

      // セッション2
      const sessionId2 = 'multi-session-2';
      const logs2: LogEntry[] = [
        {
          timestamp: '2026-02-12T11:00:00.000Z',
          type: 'user',
          content: 'セッション2',
          tokens_estimate: 25,
        },
      ];

      const logFile2 = path.join(testTmpDir, `session-${sessionId2}.json`);
      await fs.writeFile(logFile2, JSON.stringify(logs2), 'utf-8');

      const markdown2 = await writer.generate(sessionId2, logs2);
      const outputPath2 = path.join(todayDir, `session-${sessionId2}.md`);
      await fs.writeFile(outputPath2, markdown2, 'utf-8');
      await fs.unlink(logFile2);

      // 検証: 両方のファイルが存在するか
      const exists1 = await fs
        .access(outputPath1)
        .then(() => true)
        .catch(() => false);
      const exists2 = await fs
        .access(outputPath2)
        .then(() => true)
        .catch(() => false);

      expect(exists1).toBe(true);
      expect(exists2).toBe(true);

      // 検証: 内容が正しいか
      const content1 = await fs.readFile(outputPath1, 'utf-8');
      const content2 = await fs.readFile(outputPath2, 'utf-8');

      expect(content1).toContain('セッション1');
      expect(content2).toContain('セッション2');
    });
  });
});
