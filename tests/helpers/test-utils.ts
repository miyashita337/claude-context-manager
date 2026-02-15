/**
 * Test utility functions for integration tests
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import type { LogEntry } from '../../src/types/session';

export interface TestSession {
  sessionId: string;
  logFile: string;
  logs: LogEntry[];
}

/**
 * Create a test session with initial logs
 */
export async function createTestSession(
  tmpDir: string,
  sessionId: string,
  initialLogs: LogEntry[] = []
): Promise<TestSession> {
  const logFile = path.join(tmpDir, `session-${sessionId}.json`);

  await fs.writeFile(logFile, JSON.stringify(initialLogs, null, 2), 'utf-8');

  return {
    sessionId,
    logFile,
    logs: initialLogs,
  };
}

/**
 * Add a log entry to a session
 */
export async function addLogEntry(
  session: TestSession,
  entry: LogEntry
): Promise<void> {
  const currentLogs = JSON.parse(await fs.readFile(session.logFile, 'utf-8'));
  currentLogs.push(entry);

  await fs.writeFile(session.logFile, JSON.stringify(currentLogs, null, 2), 'utf-8');

  session.logs = currentLogs;
}

/**
 * Create a user log entry
 */
export function createUserEntry(content: string, timestamp?: Date): LogEntry {
  return {
    timestamp: (timestamp || new Date()).toISOString(),
    type: 'user',
    content,
    tokens_estimate: estimateTokens(content),
  };
}

/**
 * Create an assistant log entry
 */
export function createAssistantEntry(
  content: string,
  toolName?: string,
  timestamp?: Date
): LogEntry {
  const entry: LogEntry = {
    timestamp: (timestamp || new Date()).toISOString(),
    type: 'assistant',
    content,
    tokens_estimate: estimateTokens(content),
  };

  if (toolName) {
    entry.tool_name = toolName;
  }

  return entry;
}

/**
 * Simple token estimation (matching Python implementation)
 */
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

/**
 * Verify Markdown contains expected content
 */
export function verifyMarkdownContent(
  markdown: string,
  expectations: {
    sessionId?: string;
    totalTokens?: number;
    userTokens?: number;
    assistantTokens?: number;
    contentSnippets?: string[];
  }
): void {
  if (expectations.sessionId) {
    expect(markdown).toContain(`session_id: ${expectations.sessionId}`);
  }

  if (expectations.totalTokens !== undefined) {
    expect(markdown).toContain(`total_tokens: ${expectations.totalTokens}`);
  }

  if (expectations.userTokens !== undefined) {
    expect(markdown).toContain(`user_tokens: ${expectations.userTokens}`);
  }

  if (expectations.assistantTokens !== undefined) {
    expect(markdown).toContain(`assistant_tokens: ${expectations.assistantTokens}`);
  }

  if (expectations.contentSnippets) {
    for (const snippet of expectations.contentSnippets) {
      expect(markdown).toContain(snippet);
    }
  }
}

/**
 * Calculate time gap between log entries
 */
export function calculateTimeGaps(logs: LogEntry[]): Array<{
  index: number;
  gapMs: number;
  gapMinutes: number;
}> {
  const gaps: Array<{ index: number; gapMs: number; gapMinutes: number }> = [];

  for (let i = 1; i < logs.length; i++) {
    const prevTime = new Date(logs[i - 1].timestamp).getTime();
    const currTime = new Date(logs[i].timestamp).getTime();
    const gapMs = currTime - prevTime;
    const gapMinutes = gapMs / 60000;

    if (gapMinutes > 5) {
      gaps.push({ index: i, gapMs, gapMinutes });
    }
  }

  return gaps;
}

/**
 * Create test directory structure
 */
export async function setupTestDirectories(
  baseDir: string
): Promise<{
  testDir: string;
  tmpDir: string;
  sessionsDir: string;
}> {
  const testDir = path.join(baseDir, '.test-context-history');
  const tmpDir = path.join(testDir, '.tmp');
  const sessionsDir = path.join(testDir, 'sessions');

  await fs.mkdir(tmpDir, { recursive: true });
  await fs.mkdir(sessionsDir, { recursive: true });

  return { testDir, tmpDir, sessionsDir };
}

/**
 * Cleanup test directories
 */
export async function cleanupTestDirectories(testDir: string): Promise<void> {
  await fs.rm(testDir, { recursive: true, force: true });
}

/**
 * Save markdown to session directory
 */
export async function saveSessionMarkdown(
  sessionsDir: string,
  sessionId: string,
  markdown: string
): Promise<string> {
  const today = new Date().toISOString().split('T')[0];
  const outputDir = path.join(sessionsDir, today);
  await fs.mkdir(outputDir, { recursive: true });

  const outputFile = path.join(outputDir, `session-${sessionId}.md`);
  await fs.writeFile(outputFile, markdown, 'utf-8');

  return outputFile;
}

/**
 * Verify file exists
 */
export async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
