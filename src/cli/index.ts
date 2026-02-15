#!/usr/bin/env node
/**
 * Claude Context Manager CLI
 * Main entry point
 */

import { Command } from 'commander';
import { statusCommand } from './commands/status.js';
import { searchCommand } from './commands/search.js';

const program = new Command();

program
  .name('claude-context')
  .description('Claude Context Manager - Track and manage Claude conversation history')
  .version('1.0.0');

// Register commands
program
  .command('status')
  .description('Display current session token usage and statistics')
  .action(statusCommand);

program
  .command('search <keyword>')
  .description('Search session history for a keyword')
  .option('-d, --date <date>', 'Filter by date (YYYY-MM-DD)')
  .option('-r, --range <range>', 'Date range (e.g., 2026-02-01:2026-02-11)')
  .option('-t, --tokens <min>', 'Filter by minimum token count', parseInt)
  .option('-l, --limit <number>', 'Limit number of results', parseInt, 10)
  .action(searchCommand);

// Parse arguments
program.parse(process.argv);
