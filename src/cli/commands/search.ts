/**
 * Search command: Search session history
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import chalk from 'chalk';
import ora from 'ora';

interface SearchOptions {
  date?: string;
  range?: string;
  tokens?: number;
  limit?: number;
}

interface SearchResult {
  filePath: string;
  date: string;
  sessionId: string;
  lineNumber: number;
  context: string;
  matchedText: string;
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
 * Get sessions directory path
 */
function getSessionsDir(): string {
  return path.join(getHomeDir(), '.claude', 'context-history', 'sessions');
}

/**
 * Parse date range from string (e.g., "2026-02-01:2026-02-11")
 */
function parseDateRange(range: string): { start: Date; end: Date } | null {
  const parts = range.split(':');
  if (parts.length !== 2) {
    return null;
  }

  const start = new Date(parts[0]);
  const end = new Date(parts[1]);

  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return null;
  }

  return { start, end };
}

/**
 * Check if a date is within the specified range
 */
function isDateInRange(date: string, options: SearchOptions): boolean {
  if (options.date) {
    return date === options.date;
  }

  if (options.range) {
    const range = parseDateRange(options.range);
    if (!range) {
      return true; // Invalid range, include everything
    }

    const fileDate = new Date(date);
    return fileDate >= range.start && fileDate <= range.end;
  }

  return true;
}

/**
 * Search for keyword in a markdown file
 */
async function searchInFile(
  filePath: string,
  keyword: string,
  options: SearchOptions
): Promise<SearchResult[]> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content.split('\n');
    const results: SearchResult[] = [];

    // Extract metadata from frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    let totalTokens = 0;

    if (frontmatterMatch) {
      const frontmatter = frontmatterMatch[1];
      const tokensMatch = frontmatter.match(/total_tokens:\s*(\d+)/);
      if (tokensMatch) {
        totalTokens = parseInt(tokensMatch[1], 10);
      }
    }

    // Check token filter
    if (options.tokens && totalTokens < options.tokens) {
      return results;
    }

    // Extract date and session ID from file path
    const pathParts = filePath.split(path.sep);
    const date = pathParts[pathParts.length - 2]; // parent directory is the date
    const filename = path.basename(filePath);
    const sessionId = filename.replace('session-', '').replace('.md', '');

    // Search for keyword (case-insensitive)
    const keywordLower = keyword.toLowerCase();

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineLower = line.toLowerCase();

      if (lineLower.includes(keywordLower)) {
        // Get context (3 lines before and after)
        const contextStart = Math.max(0, i - 3);
        const contextEnd = Math.min(lines.length, i + 4);
        const contextLines = lines.slice(contextStart, contextEnd);

        // Highlight the matched text
        const matchedText = line.trim();

        results.push({
          filePath,
          date,
          sessionId,
          lineNumber: i + 1,
          context: contextLines.join('\n'),
          matchedText,
        });
      }
    }

    return results;
  } catch (error) {
    // File read error, skip silently
    return [];
  }
}

/**
 * Get all markdown files in sessions directory
 */
async function getAllSessionFiles(options: SearchOptions): Promise<string[]> {
  const sessionsDir = getSessionsDir();

  try {
    await fs.access(sessionsDir);
  } catch {
    return [];
  }

  try {
    const files: string[] = [];
    const dateDirs = await fs.readdir(sessionsDir);

    for (const dateDir of dateDirs) {
      // Check if this date should be included
      if (!isDateInRange(dateDir, options)) {
        continue;
      }

      const datePath = path.join(sessionsDir, dateDir);
      const stats = await fs.stat(datePath);

      if (stats.isDirectory()) {
        const sessionFiles = await fs.readdir(datePath);
        for (const file of sessionFiles) {
          if (file.endsWith('.md')) {
            files.push(path.join(datePath, file));
          }
        }
      }
    }

    return files;
  } catch (error) {
    console.error(chalk.red('Error reading sessions directory:'), error);
    return [];
  }
}

/**
 * Highlight keyword in text
 */
function highlightKeyword(text: string, keyword: string): string {
  const regex = new RegExp(`(${keyword})`, 'gi');
  return text.replace(regex, chalk.yellow.bold('$1'));
}

/**
 * Format search result for display
 */
function formatSearchResult(result: SearchResult, keyword: string, index: number): string {
  const output: string[] = [];

  // Header
  output.push(chalk.cyan.bold(`\n[${index + 1}] ${result.date} - Session ${result.sessionId}`));
  output.push(chalk.gray(`File: ${result.filePath}`));
  output.push(chalk.gray(`Line: ${result.lineNumber}`));

  // Matched line with highlighting
  output.push(chalk.white('\nMatched line:'));
  output.push(highlightKeyword(result.matchedText, keyword));

  // Context
  output.push(chalk.white('\nContext:'));
  output.push(chalk.gray(result.context));

  output.push(chalk.gray('─'.repeat(75)));

  return output.join('\n');
}

/**
 * Search command handler
 */
export async function searchCommand(keyword: string, options: SearchOptions): Promise<void> {
  if (!keyword || keyword.trim().length === 0) {
    console.error(chalk.red('Error: Keyword is required'));
    process.exit(1);
  }

  const spinner = ora('Searching session history...').start();

  try {
    // Get all session files
    const files = await getAllSessionFiles(options);

    if (files.length === 0) {
      spinner.stop();
      console.log(chalk.yellow('No session files found.'));
      console.log(chalk.gray(`Sessions are stored in: ${getSessionsDir()}`));
      return;
    }

    // Search in each file
    const allResults: SearchResult[] = [];

    for (const file of files) {
      const results = await searchInFile(file, keyword, options);
      allResults.push(...results);
    }

    spinner.stop();

    if (allResults.length === 0) {
      console.log(chalk.yellow(`No results found for keyword: "${keyword}"`));
      return;
    }

    // Apply limit
    const limit = options.limit || 10;
    const displayResults = allResults.slice(0, limit);

    // Display results
    console.log(chalk.bold.cyan(`\n🔍 Search Results for "${keyword}"\n`));
    console.log(chalk.gray(`Found ${allResults.length} result(s), showing first ${displayResults.length}\n`));

    for (let i = 0; i < displayResults.length; i++) {
      console.log(formatSearchResult(displayResults[i], keyword, i));
    }

    // Summary
    if (allResults.length > displayResults.length) {
      console.log(
        chalk.yellow(`\n... ${allResults.length - displayResults.length} more result(s) not shown.`)
      );
      console.log(chalk.gray(`Use --limit option to show more results.\n`));
    }

  } catch (error) {
    spinner.stop();
    console.error(chalk.red('Error:'), error instanceof Error ? error.message : error);
    process.exit(1);
  }
}
