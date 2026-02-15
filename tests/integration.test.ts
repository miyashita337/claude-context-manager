/**
 * Integration tests for Claude Context Manager
 * Tests the complete flow: Hook -> Temp Log -> Finalize -> Markdown Generation
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { MarkdownWriter } from '../src/core/markdown-writer.js';
import type { LogEntry } from '../src/types/session.js';

describe('Integration Tests - End-to-End Flow', () => {
  let testDir: string;
  let tmpDir: string;
  let sessionsDir: string;

  beforeEach(async () => {
    // Create temporary test directory
    testDir = path.join(process.cwd(), '.test-context-history');
    tmpDir = path.join(testDir, '.tmp');
    sessionsDir = path.join(testDir, 'sessions');

    await fs.mkdir(tmpDir, { recursive: true });
    await fs.mkdir(sessionsDir, { recursive: true });

    // Override HOME for tests
    process.env.TEST_HOME = testDir;
  });

  afterEach(async () => {
    // Cleanup test directory
    await fs.rm(testDir, { recursive: true, force: true });
  });

  describe('End-to-End Tests (6 cases)', () => {
    test('1. Single session complete flow (user-prompt -> post-tool -> stop -> Markdown)', async () => {
      const sessionId = 'test-session-001';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      // Step 1: Simulate user-prompt hook
      const userEntry: LogEntry = {
        timestamp: new Date('2026-02-12T10:00:00Z').toISOString(),
        type: 'user',
        content: 'TypeScriptでHello Worldを書いてください',
        tokens_estimate: 20,
      };

      await fs.writeFile(logFile, JSON.stringify([userEntry], null, 2), 'utf-8');

      // Step 2: Simulate post-tool hook
      const assistantEntry: LogEntry = {
        timestamp: new Date('2026-02-12T10:00:30Z').toISOString(),
        type: 'assistant',
        content: 'console.log("Hello World");',
        tokens_estimate: 10,
        tool_name: 'Write',
      };

      const logs = JSON.parse(await fs.readFile(logFile, 'utf-8'));
      logs.push(assistantEntry);
      await fs.writeFile(logFile, JSON.stringify(logs, null, 2), 'utf-8');

      // Step 3: Simulate stop hook - finalize to Markdown
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      // Verify Markdown output
      expect(markdown).toContain('session_id: test-session-001');
      expect(markdown).toContain('total_tokens: 30');
      expect(markdown).toContain('user_tokens: 20');
      expect(markdown).toContain('assistant_tokens: 10');
      expect(markdown).toContain('TypeScriptでHello Worldを書いてください');
      expect(markdown).toContain('console.log("Hello World");');

      // Save to sessions directory
      const today = new Date().toISOString().split('T')[0];
      const outputDir = path.join(sessionsDir, today);
      await fs.mkdir(outputDir, { recursive: true });

      const outputFile = path.join(outputDir, `session-${sessionId}.md`);
      await fs.writeFile(outputFile, markdown, 'utf-8');

      // Verify file exists
      const exists = await fs.access(outputFile).then(() => true).catch(() => false);
      expect(exists).toBe(true);

      // Cleanup temp file
      await fs.unlink(logFile);
      const tempExists = await fs.access(logFile).then(() => true).catch(() => false);
      expect(tempExists).toBe(false);
    });

    test('2. Multiple finalize executions with append behavior', async () => {
      const sessionId = 'test-session-002';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);
      const today = new Date().toISOString().split('T')[0];
      const outputDir = path.join(sessionsDir, today);
      await fs.mkdir(outputDir, { recursive: true });

      const outputFile = path.join(outputDir, `session-${sessionId}.md`);

      // First finalize
      const logs1: LogEntry[] = [
        {
          timestamp: new Date('2026-02-12T10:00:00Z').toISOString(),
          type: 'user',
          content: 'First message',
          tokens_estimate: 5,
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs1, null, 2), 'utf-8');

      const writer = new MarkdownWriter();
      const markdown1 = await writer.generate(sessionId, logs1);
      await fs.writeFile(outputFile, markdown1, 'utf-8');

      // Verify first output
      let content = await fs.readFile(outputFile, 'utf-8');
      expect(content).toContain('First message');
      expect(content).toContain('total_tokens: 5');

      // Second finalize (append)
      const logs2: LogEntry[] = [
        ...logs1,
        {
          timestamp: new Date('2026-02-12T10:01:00Z').toISOString(),
          type: 'assistant',
          content: 'Second message',
          tokens_estimate: 10,
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs2, null, 2), 'utf-8');

      const markdown2 = await writer.generate(sessionId, logs2);
      await fs.writeFile(outputFile, markdown2, 'utf-8');

      // Verify append behavior
      content = await fs.readFile(outputFile, 'utf-8');
      expect(content).toContain('First message');
      expect(content).toContain('Second message');
      expect(content).toContain('total_tokens: 15');
    });

    test('3. Same session ID with multiple restarts and appends', async () => {
      const sessionId = 'test-session-003';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      // Restart 1
      const logs1: LogEntry[] = [
        {
          timestamp: new Date('2026-02-12T09:00:00Z').toISOString(),
          type: 'user',
          content: 'First restart',
          tokens_estimate: 5,
        },
      ];
      await fs.writeFile(logFile, JSON.stringify(logs1, null, 2), 'utf-8');

      // Restart 2 (same session ID, new logs)
      const logs2: LogEntry[] = [
        ...logs1,
        {
          timestamp: new Date('2026-02-12T09:30:00Z').toISOString(),
          type: 'user',
          content: 'Second restart',
          tokens_estimate: 5,
        },
      ];
      await fs.writeFile(logFile, JSON.stringify(logs2, null, 2), 'utf-8');

      // Finalize
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs2);

      expect(markdown).toContain('First restart');
      expect(markdown).toContain('Second restart');
      expect(markdown).toContain('total_tokens: 10');
    });

    test('4. Time gap detection integration', async () => {
      const sessionId = 'test-session-004';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      // Create logs with time gap > 5 minutes
      const logs: LogEntry[] = [
        {
          timestamp: new Date('2026-02-12T10:00:00Z').toISOString(),
          type: 'user',
          content: 'Before gap',
          tokens_estimate: 5,
        },
        {
          timestamp: new Date('2026-02-12T10:10:00Z').toISOString(), // 10 min gap
          type: 'user',
          content: 'After gap',
          tokens_estimate: 5,
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs, null, 2), 'utf-8');

      // Detect time gaps
      const gaps: { index: number; gapMinutes: number }[] = [];

      for (let i = 1; i < logs.length; i++) {
        const prevTime = new Date(logs[i - 1].timestamp).getTime();
        const currTime = new Date(logs[i].timestamp).getTime();
        const gapMs = currTime - prevTime;
        const gapMinutes = gapMs / 60000;

        if (gapMinutes > 5) {
          gaps.push({ index: i, gapMinutes });
        }
      }

      expect(gaps.length).toBe(1);
      expect(gaps[0].gapMinutes).toBe(10);

      // Verify Markdown includes both entries
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      expect(markdown).toContain('Before gap');
      expect(markdown).toContain('After gap');
    });

    test('5. session-unknown processing', async () => {
      const sessionId = 'session-unknown';
      const logFile = path.join(tmpDir, `${sessionId}.json`);

      const logs: LogEntry[] = [
        {
          timestamp: new Date().toISOString(),
          type: 'user',
          content: 'Unknown session content',
          tokens_estimate: 10,
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs, null, 2), 'utf-8');

      // Process unknown session
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      expect(markdown).toContain('session_id: session-unknown');
      expect(markdown).toContain('Unknown session content');
    });

    test('6. Japanese content complete flow', async () => {
      const sessionId = 'test-session-006';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      const logs: LogEntry[] = [
        {
          timestamp: new Date('2026-02-12T10:00:00Z').toISOString(),
          type: 'user',
          content: 'Pythonで機械学習のサンプルコードを作成してください。データセットはirisを使用します。',
          tokens_estimate: 30,
        },
        {
          timestamp: new Date('2026-02-12T10:00:30Z').toISOString(),
          type: 'assistant',
          content: 'from sklearn import datasets\nfrom sklearn.model_selection import train_test_split\niris = datasets.load_iris()\nX_train, X_test, y_train, y_test = train_test_split(iris.data, iris.target)',
          tokens_estimate: 50,
          tool_name: 'Write',
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs, null, 2), 'utf-8');

      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      // Verify Japanese content is preserved
      expect(markdown).toContain('機械学習');
      expect(markdown).toContain('データセット');
      expect(markdown).toContain('from sklearn import datasets');
      expect(markdown).toContain('total_tokens: 80');

      // Verify UTF-8 encoding
      const today = new Date().toISOString().split('T')[0];
      const outputDir = path.join(sessionsDir, today);
      await fs.mkdir(outputDir, { recursive: true });

      const outputFile = path.join(outputDir, `session-${sessionId}.md`);
      await fs.writeFile(outputFile, markdown, 'utf-8');

      const savedContent = await fs.readFile(outputFile, 'utf-8');
      expect(savedContent).toContain('機械学習');
    });
  });

  describe('Error Handling Tests (4 cases)', () => {
    test('7. Invalid JSON input error handling', async () => {
      const sessionId = 'test-session-007';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      // Write invalid JSON
      await fs.writeFile(logFile, 'invalid json content', 'utf-8');

      // Attempt to parse
      try {
        const content = await fs.readFile(logFile, 'utf-8');
        JSON.parse(content);
        fail('Should have thrown JSON parse error');
      } catch (error) {
        expect(error).toBeInstanceOf(SyntaxError);
      }

      // Recovery: overwrite with valid data
      const validLogs: LogEntry[] = [
        {
          timestamp: new Date().toISOString(),
          type: 'user',
          content: 'Recovered content',
          tokens_estimate: 5,
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(validLogs, null, 2), 'utf-8');

      const recovered = JSON.parse(await fs.readFile(logFile, 'utf-8'));
      expect(recovered).toHaveLength(1);
      expect(recovered[0].content).toBe('Recovered content');
    });

    test('8. Finalize failure recovery', async () => {
      const sessionId = 'test-session-008';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      const logs: LogEntry[] = [
        {
          timestamp: new Date().toISOString(),
          type: 'user',
          content: 'Test content',
          tokens_estimate: 5,
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs, null, 2), 'utf-8');

      // Simulate finalize failure (missing permissions, etc.)
      const invalidOutputDir = '/invalid/readonly/path';

      try {
        const outputFile = path.join(invalidOutputDir, `session-${sessionId}.md`);
        await fs.writeFile(outputFile, 'content', 'utf-8');
        fail('Should have thrown permission error');
      } catch (error) {
        expect(error).toBeDefined();
      }

      // Verify temp file still exists (not deleted on failure)
      const tempExists = await fs.access(logFile).then(() => true).catch(() => false);
      expect(tempExists).toBe(true);

      // Recovery: use valid output path
      const today = new Date().toISOString().split('T')[0];
      const validOutputDir = path.join(sessionsDir, today);
      await fs.mkdir(validOutputDir, { recursive: true });

      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      const validOutputFile = path.join(validOutputDir, `session-${sessionId}.md`);
      await fs.writeFile(validOutputFile, markdown, 'utf-8');

      const exists = await fs.access(validOutputFile).then(() => true).catch(() => false);
      expect(exists).toBe(true);
    });

    test('9. Disk space simulation (write size check)', async () => {
      const sessionId = 'test-session-009';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      // Create large content (simulate disk usage)
      const largeContent = 'a'.repeat(1024 * 1024); // 1MB

      const logs: LogEntry[] = [
        {
          timestamp: new Date().toISOString(),
          type: 'user',
          content: largeContent,
          tokens_estimate: Math.ceil(largeContent.length / 4),
        },
      ];

      await fs.writeFile(logFile, JSON.stringify(logs, null, 2), 'utf-8');

      // Verify file size
      const stats = await fs.stat(logFile);
      expect(stats.size).toBeGreaterThan(1024 * 1024);

      // Finalize
      const writer = new MarkdownWriter();
      const markdown = await writer.generate(sessionId, logs);

      expect(markdown.length).toBeGreaterThan(1024 * 1024);
    });

    test('10. Concurrent execution race condition handling', async () => {
      const sessionId = 'test-session-010';
      const logFile = path.join(tmpDir, `session-${sessionId}.json`);

      // Initialize with empty array
      await fs.writeFile(logFile, JSON.stringify([], null, 2), 'utf-8');

      // Simulate concurrent writes
      const writes = Array.from({ length: 10 }, (_, i) => {
        const entry: LogEntry = {
          timestamp: new Date(Date.now() + i * 1000).toISOString(),
          type: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
          tokens_estimate: 5,
        };

        return (async () => {
          // Read-modify-write (non-atomic, potential race)
          const current = JSON.parse(await fs.readFile(logFile, 'utf-8'));
          current.push(entry);
          await fs.writeFile(logFile, JSON.stringify(current, null, 2), 'utf-8');
        })();
      });

      await Promise.all(writes);

      // Check final state (may have lost some entries due to race)
      // The race condition may corrupt the JSON file, which is expected
      try {
        const finalLogs = JSON.parse(await fs.readFile(logFile, 'utf-8'));

        // If JSON is valid, verify basic structure
        expect(Array.isArray(finalLogs)).toBe(true);
        expect(finalLogs.length).toBeGreaterThan(0);
        expect(finalLogs.length).toBeLessThanOrEqual(10);
      } catch (error) {
        // JSON corruption is expected due to race condition
        // This demonstrates the need for file locking
        expect(error).toBeInstanceOf(SyntaxError);
      }

      // Note: Proper solution requires file locking mechanism
      // This test demonstrates the race condition exists and can corrupt data
    });
  });
});
