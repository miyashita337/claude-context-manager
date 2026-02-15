/**
 * Markdown generation for session logs
 */

import type { LogEntry, SessionStats } from '../types/session.js';

export class MarkdownWriter {
  /**
   * Generate markdown from session logs
   */
  async generate(sessionId: string, logs: LogEntry[]): Promise<string> {
    if (logs.length === 0) {
      throw new Error('No logs to generate markdown from');
    }

    const firstLog = logs[0];
    const lastLog = logs[logs.length - 1];

    const startTime = new Date(firstLog.timestamp);
    const endTime = new Date(lastLog.timestamp);

    // Calculate statistics
    const stats = this.calculateStats(logs, startTime, endTime);

    // Generate markdown
    let markdown = this.generateFrontmatter(sessionId, startTime, stats);
    markdown += this.generateHeader(startTime);
    markdown += this.generateLogEntries(logs);
    markdown += this.generateStatistics(stats);

    return markdown;
  }

  /**
   * Calculate session statistics
   */
  private calculateStats(
    logs: LogEntry[],
    startTime: Date,
    endTime: Date
  ): SessionStats {
    const totalTokens = logs.reduce(
      (sum, log) => sum + (log.tokens_estimate || 0),
      0
    );

    const userTokens = logs
      .filter((l) => l.type === 'user')
      .reduce((sum, log) => sum + (log.tokens_estimate || 0), 0);

    const assistantTokens = logs
      .filter((l) => l.type === 'assistant')
      .reduce((sum, log) => sum + (log.tokens_estimate || 0), 0);

    const durationMs = endTime.getTime() - startTime.getTime();
    const durationMinutes = Math.round(durationMs / 60000);

    return {
      total_tokens: totalTokens,
      user_tokens: userTokens,
      assistant_tokens: assistantTokens,
      entry_count: logs.length,
      duration_minutes: durationMinutes,
    };
  }

  /**
   * Generate frontmatter
   */
  private generateFrontmatter(
    sessionId: string,
    startTime: Date,
    stats: SessionStats
  ): string {
    return `---
date: ${startTime.toISOString()}
session_id: ${sessionId}
total_tokens: ${stats.total_tokens}
user_tokens: ${stats.user_tokens}
assistant_tokens: ${stats.assistant_tokens}
compact_detected: false
tags: [claude, conversation]
---

`;
  }

  /**
   * Generate header
   */
  private generateHeader(startTime: Date): string {
    const dateStr = startTime.toISOString().split('T')[0];
    return `# Claude対話履歴 - ${dateStr}\n\n`;
  }

  /**
   * Generate log entries
   */
  private generateLogEntries(logs: LogEntry[]): string {
    let markdown = '';

    for (const log of logs) {
      const time = new Date(log.timestamp).toLocaleTimeString('ja-JP');
      const role =
        log.type === 'user'
          ? 'ユーザー'
          : `Claude${log.tool_name ? ` (${log.tool_name})` : ''}`;

      markdown += `\n## ${time} - ${role}\n\n`;
      markdown += `${log.content}\n\n`;
      markdown += `**Tokens**: ${log.tokens_estimate} (推定)\n`;
    }

    return markdown;
  }

  /**
   * Generate statistics section
   */
  private generateStatistics(stats: SessionStats): string {
    return `
---

**セッション統計**:
- 総Token数: ${stats.total_tokens} (推定)
- ユーザーToken: ${stats.user_tokens}
- ClaudeToken: ${stats.assistant_tokens}
- Compact: なし
- セッション時間: ${stats.duration_minutes}分
- エントリ数: ${stats.entry_count}
`;
  }

  /**
   * Generate incremental markdown from session logs
   * Appends to existing content if provided
   */
  async generateIncremental(
    sessionId: string,
    logs: LogEntry[],
    existingContent?: string
  ): Promise<string> {
    if (logs.length === 0) {
      throw new Error('No logs to generate markdown from');
    }

    // If no existing content, generate from scratch
    if (!existingContent) {
      return this.generate(sessionId, logs);
    }

    // Parse existing content
    const { frontmatter, body, existingLogs } = this.parseExistingMarkdown(existingContent);

    // Merge logs and detect time gaps
    const mergedBody = this.appendLogsWithTimeGaps(existingLogs, logs, body);

    // Recalculate statistics for all logs
    const allLogs = [...existingLogs, ...logs];
    const firstLog = allLogs[0];
    const lastLog = allLogs[allLogs.length - 1];
    const startTime = new Date(firstLog.timestamp);
    const endTime = new Date(lastLog.timestamp);
    const stats = this.calculateStats(allLogs, startTime, endTime);

    // Merge frontmatter with new stats
    const updatedFrontmatter = this.mergeFrontmatter(frontmatter, stats);

    // Regenerate statistics section
    const statisticsSection = this.generateStatistics(stats);

    // Combine all parts
    return updatedFrontmatter + mergedBody + statisticsSection;
  }

  /**
   * Parse existing markdown to extract frontmatter, body, and logs
   */
  private parseExistingMarkdown(content: string): {
    frontmatter: Record<string, any>;
    body: string;
    existingLogs: LogEntry[];
  } {
    // Extract frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---\n/);
    const frontmatter: Record<string, any> = {};

    if (frontmatterMatch) {
      const frontmatterText = frontmatterMatch[1];
      frontmatterText.split('\n').forEach(line => {
        const match = line.match(/^(\w+):\s*(.+)$/);
        if (match) {
          const key = match[1];
          let value: any = match[2];

          // Parse numbers
          if (!isNaN(Number(value))) {
            value = Number(value);
          }
          // Parse booleans
          else if (value === 'true' || value === 'false') {
            value = value === 'true';
          }
          // Parse arrays
          else if (value.startsWith('[') && value.endsWith(']')) {
            value = value.slice(1, -1).split(',').map((v: string) => v.trim());
          }

          frontmatter[key] = value;
        }
      });
    }

    // Extract body (everything between frontmatter and statistics section)
    const bodyMatch = content.match(/---\n\n([\s\S]*?)(?:\n---\n\n\*\*セッション統計\*\*:|$)/);
    const body = bodyMatch ? bodyMatch[1] : '';

    // Extract existing log entries to get timestamps
    const existingLogs: LogEntry[] = [];
    const logPattern = /## (\d{2}:\d{2}:\d{2}) - (ユーザー|Claude(?:\s*\([^)]+\))?)\n\n([\s\S]*?)\n\n\*\*Tokens\*\*:\s*(\d+)/g;
    let match;

    while ((match = logPattern.exec(body)) !== null) {
      const timeStr = match[1];
      const role = match[2];
      const content = match[3];
      const tokens = parseInt(match[4], 10);

      // Reconstruct approximate timestamp using frontmatter date
      const date = frontmatter.date ? new Date(frontmatter.date) : new Date();
      const [hours, minutes, seconds] = timeStr.split(':').map(Number);
      const timestamp = new Date(date);
      timestamp.setHours(hours, minutes, seconds, 0);

      existingLogs.push({
        timestamp: timestamp.toISOString(),
        type: role.startsWith('ユーザー') ? 'user' : 'assistant',
        content: content,
        tokens_estimate: tokens,
        tool_name: role.includes('(') ? role.match(/\(([^)]+)\)/)?.[1] : undefined
      });
    }

    return { frontmatter, body, existingLogs };
  }

  /**
   * Append new logs to existing body with time gap detection
   */
  private appendLogsWithTimeGaps(
    existingLogs: LogEntry[],
    newLogs: LogEntry[],
    existingBody: string
  ): string {
    // Remove the header from existing body
    let body = existingBody.replace(/^# Claude対話履歴 - \d{4}-\d{2}-\d{2}\n\n/, '');

    // Remove trailing statistics section if present
    body = body.replace(/\n---\n\n\*\*セッション統計\*\*:[\s\S]*$/, '');

    // Add header back
    const firstLog = existingLogs.length > 0 ? existingLogs[0] : newLogs[0];
    const startTime = new Date(firstLog.timestamp);
    let result = this.generateHeader(startTime);
    result += body;

    // Detect time gap between last existing log and first new log
    if (existingLogs.length > 0 && newLogs.length > 0) {
      const lastExistingTime = new Date(existingLogs[existingLogs.length - 1].timestamp);
      const firstNewTime = new Date(newLogs[0].timestamp);
      const gapMs = firstNewTime.getTime() - lastExistingTime.getTime();
      const gapMinutes = Math.round(gapMs / 60000);

      // Insert separator if gap is 30 minutes or more
      if (gapMinutes >= 30) {
        const hours = Math.floor(gapMinutes / 60);
        const minutes = gapMinutes % 60;
        const gapText = hours > 0
          ? `${hours}時間${minutes}分の間隔`
          : `${minutes}分の間隔`;

        result += `\n---\n<!-- ${gapText} -->\n---\n`;
      }
    }

    // Append new log entries
    result += this.generateLogEntries(newLogs);

    return result;
  }

  /**
   * Merge existing frontmatter with new statistics
   */
  mergeFrontmatter(
    existingFrontmatter: Record<string, any>,
    newStats: SessionStats
  ): string {
    // Update with new statistics
    const merged: Record<string, any> = {
      ...existingFrontmatter,
      total_tokens: newStats.total_tokens,
      user_tokens: newStats.user_tokens,
      assistant_tokens: newStats.assistant_tokens
    };

    // Generate frontmatter string
    let frontmatter = '---\n';

    // Preserve order: date, session_id, tokens, compact_detected, tags
    const orderedKeys = ['date', 'session_id', 'total_tokens', 'user_tokens', 'assistant_tokens', 'compact_detected', 'tags'];

    for (const key of orderedKeys) {
      if (merged[key] !== undefined) {
        let value: any = merged[key];

        // Format arrays
        if (Array.isArray(value)) {
          value = `[${value.join(', ')}]`;
        }

        frontmatter += `${key}: ${value}\n`;
      }
    }

    frontmatter += '---\n\n';
    return frontmatter;
  }
}
