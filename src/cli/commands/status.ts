/**
 * Status command: Display current session token usage
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import chalk from 'chalk';
import Table from 'cli-table3';
import ora from 'ora';
import type { LogEntry } from '../../types/session.js';

interface SessionInfo {
  sessionId: string;
  filePath: string;
  totalTokens: number;
  userTokens: number;
  assistantTokens: number;
  entryCount: number;
  startTime: string | null;
  lastUpdate: string | null;
}

/**
 * Get home directory path
 */
function getHomeDir(): string {
  const homeDir = process.env.HOME || process.env.USERPROFILE;
  if (!homeDir) {
    throw new Error('HOME environment variable not set');
  }
  return homeDir;
}

/**
 * Get temporary directory path
 */
function getTmpDir(): string {
  return path.join(getHomeDir(), '.claude', 'context-history', '.tmp');
}

/**
 * Read session data from a log file
 */
async function readSessionData(filePath: string): Promise<SessionInfo | null> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    const logs: LogEntry[] = JSON.parse(content);

    if (logs.length === 0) {
      return null;
    }

    // Calculate token statistics
    let totalTokens = 0;
    let userTokens = 0;
    let assistantTokens = 0;

    for (const log of logs) {
      totalTokens += log.tokens_estimate;
      if (log.type === 'user') {
        userTokens += log.tokens_estimate;
      } else if (log.type === 'assistant') {
        assistantTokens += log.tokens_estimate;
      }
    }

    // Extract session ID from filename
    const filename = path.basename(filePath);
    const sessionId = filename.replace('session-', '').replace('.json', '');

    return {
      sessionId,
      filePath,
      totalTokens,
      userTokens,
      assistantTokens,
      entryCount: logs.length,
      startTime: logs[0]?.timestamp || null,
      lastUpdate: logs[logs.length - 1]?.timestamp || null,
    };
  } catch (error) {
    console.error(chalk.red(`Error reading ${filePath}:`), error);
    return null;
  }
}

/**
 * Get all active sessions from temporary directory
 */
async function getActiveSessions(): Promise<SessionInfo[]> {
  const tmpDir = getTmpDir();

  try {
    await fs.access(tmpDir);
  } catch {
    // Directory doesn't exist yet
    return [];
  }

  try {
    const files = await fs.readdir(tmpDir);
    const sessionFiles = files.filter((file) => file.startsWith('session-') && file.endsWith('.json'));

    const sessions: SessionInfo[] = [];
    for (const file of sessionFiles) {
      const filePath = path.join(tmpDir, file);
      const sessionInfo = await readSessionData(filePath);
      if (sessionInfo) {
        sessions.push(sessionInfo);
      }
    }

    // Sort by last update time (most recent first)
    sessions.sort((a, b) => {
      if (!a.lastUpdate || !b.lastUpdate) return 0;
      return new Date(b.lastUpdate).getTime() - new Date(a.lastUpdate).getTime();
    });

    return sessions;
  } catch (error) {
    console.error(chalk.red('Error reading temporary directory:'), error);
    return [];
  }
}

/**
 * Format token count with color coding
 */
function formatTokens(tokens: number): string {
  if (tokens > 50000) {
    return chalk.red.bold(tokens.toLocaleString());
  } else if (tokens > 30000) {
    return chalk.yellow(tokens.toLocaleString());
  } else {
    return chalk.green(tokens.toLocaleString());
  }
}

/**
 * Get warning message for token count
 */
function getTokenWarning(tokens: number): string | null {
  if (tokens > 50000) {
    return chalk.red.bold('⚠ WARNING: High risk of Lost-in-the-middle problem! Consider starting a new session.');
  } else if (tokens > 30000) {
    return chalk.yellow('⚠ CAUTION: Approaching context limit. Monitor token usage carefully.');
  }
  return null;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) return 'N/A';
  const date = new Date(timestamp);
  return date.toLocaleString();
}

/**
 * Status command handler
 */
export async function statusCommand(): Promise<void> {
  const spinner = ora('Loading session data...').start();

  try {
    const sessions = await getActiveSessions();
    spinner.stop();

    if (sessions.length === 0) {
      console.log(chalk.yellow('No active sessions found.'));
      console.log(chalk.gray(`Temporary logs are stored in: ${getTmpDir()}`));
      return;
    }

    console.log(chalk.bold.cyan('\n📊 Active Claude Sessions\n'));

    // Display each session
    for (const session of sessions) {
      const table = new Table({
        head: [chalk.cyan('Metric'), chalk.cyan('Value')],
        colWidths: [25, 50],
      });

      table.push(
        ['Session ID', chalk.white(session.sessionId)],
        ['Total Tokens', formatTokens(session.totalTokens)],
        ['User Tokens', chalk.blue(session.userTokens.toLocaleString())],
        ['Assistant Tokens', chalk.magenta(session.assistantTokens.toLocaleString())],
        ['Entry Count', chalk.white(session.entryCount.toString())],
        ['Start Time', chalk.gray(formatTimestamp(session.startTime))],
        ['Last Update', chalk.gray(formatTimestamp(session.lastUpdate))]
      );

      console.log(table.toString());

      // Display warning if needed
      const warning = getTokenWarning(session.totalTokens);
      if (warning) {
        console.log('\n' + warning + '\n');
      }

      console.log(chalk.gray('─'.repeat(75)) + '\n');
    }

    // Summary statistics
    const totalTokensAll = sessions.reduce((sum, s) => sum + s.totalTokens, 0);
    const totalEntries = sessions.reduce((sum, s) => sum + s.entryCount, 0);

    console.log(chalk.bold.cyan('📈 Summary Statistics\n'));
    const summaryTable = new Table({
      head: [chalk.cyan('Metric'), chalk.cyan('Value')],
      colWidths: [25, 50],
    });

    summaryTable.push(
      ['Total Active Sessions', chalk.white(sessions.length.toString())],
      ['Total Tokens (All Sessions)', formatTokens(totalTokensAll)],
      ['Total Entries', chalk.white(totalEntries.toString())],
      ['Average Tokens/Session', chalk.white(Math.round(totalTokensAll / sessions.length).toLocaleString())]
    );

    console.log(summaryTable.toString());
    console.log(chalk.gray(`\nData location: ${getTmpDir()}\n`));

  } catch (error) {
    spinner.stop();
    console.error(chalk.red('Error:'), error instanceof Error ? error.message : error);
    process.exit(1);
  }
}
