#!/usr/bin/env node
/**
 * Finalize session: convert temporary JSON logs to Markdown
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { MarkdownWriter } from '../core/markdown-writer.js';
import type { LogEntry } from '../types/session.js';

async function main() {
  const sessionId = process.argv[2];

  if (!sessionId) {
    console.error('Error: Session ID required');
    console.error('Usage: finalize-session.ts <session-id>');
    process.exit(1);
  }

  try {
    const homeDir = process.env.HOME || process.env.USERPROFILE;
    if (!homeDir) {
      throw new Error('HOME environment variable not set');
    }

    // Paths
    const tmpDir = path.join(homeDir, '.claude', 'context-history', '.tmp');
    const logFile = path.join(tmpDir, `session-${sessionId}.json`);

    // Check if log file exists
    try {
      await fs.access(logFile);
    } catch {
      console.log(`No logs found for session ${sessionId}`);
      process.exit(0);
    }

    // Read temporary logs (JSON Lines format: one JSON per line)
    const logsContent = await fs.readFile(logFile, 'utf-8');
    const logs: LogEntry[] = logsContent
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line));

    if (logs.length === 0) {
      console.log(`No entries in session ${sessionId}`);
      await fs.unlink(logFile);
      process.exit(0);
    }

    // Determine output path
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    const outputDir = path.join(
      homeDir,
      '.claude',
      'context-history',
      'sessions',
      today
    );

    // Ensure output directory exists
    await fs.mkdir(outputDir, { recursive: true });

    // Check if output file already exists
    const outputFile = path.join(outputDir, `session-${sessionId}.md`);
    let existingContent: string | undefined;

    try {
      existingContent = await fs.readFile(outputFile, 'utf-8');
      console.log(`Appending to existing session: ${outputFile}`);
    } catch {
      console.log(`Creating new session: ${outputFile}`);
    }

    // Generate Markdown (incremental if existing content found)
    const writer = new MarkdownWriter();
    const markdown = await writer.generateIncremental(
      sessionId,
      logs,
      existingContent
    );

    // Write markdown file
    await fs.writeFile(outputFile, markdown, 'utf-8');

    // Delete temporary log file
    await fs.unlink(logFile);

    console.log(`Session finalized: ${outputFile}`);
  } catch (error) {
    console.error('Error finalizing session:', error);
    process.exit(1);
  }
}

main();
