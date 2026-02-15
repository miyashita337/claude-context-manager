#!/usr/bin/env node
/**
 * Test script for incremental markdown generation
 */

import { MarkdownWriter } from './src/core/markdown-writer.js';
import type { LogEntry } from './src/types/session.js';

async function testIncremental() {
  const writer = new MarkdownWriter();

  // Create initial logs
  const initialLogs: LogEntry[] = [
    {
      timestamp: new Date('2026-02-12T10:00:00').toISOString(),
      type: 'user',
      content: '最初のメッセージです',
      tokens_estimate: 100
    },
    {
      timestamp: new Date('2026-02-12T10:01:00').toISOString(),
      type: 'assistant',
      content: '了解しました。最初の応答です。',
      tokens_estimate: 150
    }
  ];

  // Generate initial markdown
  console.log('=== Generating initial markdown ===');
  const initialMarkdown = await writer.generate('test-session-001', initialLogs);
  console.log(initialMarkdown);
  console.log('\n' + '='.repeat(60) + '\n');

  // Create new logs with 35 minute gap
  const newLogs: LogEntry[] = [
    {
      timestamp: new Date('2026-02-12T10:36:00').toISOString(),
      type: 'user',
      content: '35分後の新しいメッセージです',
      tokens_estimate: 120
    },
    {
      timestamp: new Date('2026-02-12T10:37:00').toISOString(),
      type: 'assistant',
      content: '新しい応答です。',
      tokens_estimate: 180
    }
  ];

  // Generate incremental markdown (should include time gap separator)
  console.log('=== Generating incremental markdown (with time gap) ===');
  const incrementalMarkdown = await writer.generateIncremental(
    'test-session-001',
    newLogs,
    initialMarkdown
  );
  console.log(incrementalMarkdown);
  console.log('\n' + '='.repeat(60) + '\n');

  // Create another set of logs without large gap (5 minutes later)
  const moreLogs: LogEntry[] = [
    {
      timestamp: new Date('2026-02-12T10:42:00').toISOString(),
      type: 'user',
      content: '5分後の追加メッセージです',
      tokens_estimate: 110
    },
    {
      timestamp: new Date('2026-02-12T10:43:00').toISOString(),
      type: 'assistant',
      content: 'さらに追加の応答です。',
      tokens_estimate: 160
    }
  ];

  // Generate incremental markdown (should NOT include time gap separator)
  console.log('=== Generating incremental markdown (without time gap) ===');
  const finalMarkdown = await writer.generateIncremental(
    'test-session-001',
    moreLogs,
    incrementalMarkdown
  );
  console.log(finalMarkdown);
  console.log('\n' + '='.repeat(60) + '\n');

  console.log('✓ Test completed successfully!');
}

testIncremental().catch(error => {
  console.error('Error:', error);
  process.exit(1);
});
