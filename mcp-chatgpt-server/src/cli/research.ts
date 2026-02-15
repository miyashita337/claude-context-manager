#!/usr/bin/env node

import { Command } from 'commander';
import { performWebResearch } from '../tools/web-research.js';
import { formatResearchAsMarkdown } from '../formatters/markdown-formatter.js';
import { saveResearch } from '../utils/file-manager.js';

const program = new Command();

program
  .name('research-tool')
  .description('Perform web research with citations using ChatGPT or Gemini')
  .version('1.0.0')
  .argument('<query>', 'Research topic or question')
  .option('--model <model>', 'Model provider: openai, gemini, or specific model name (gpt-4o, gemini-2.5-flash)', 'openai')
  .option('--grounding', 'Enable Google Search grounding (Gemini only)', false)
  .action(async (query: string, options: { model: string; grounding: boolean }) => {
    try {
      // モデル名の正規化
      let model = options.model;
      let provider: 'openai' | 'gemini' | undefined;

      // プロバイダー名が直接指定された場合
      if (model === 'openai') {
        model = 'gpt-4o';
        provider = 'openai';
      } else if (model === 'gemini') {
        model = 'gemini-2.5-flash';
        provider = 'gemini';
      }

      // 実行中のモデルを表示
      const providerDisplay = provider || (model.startsWith('gemini') ? 'gemini' : 'openai');
      console.error(`🔍 Researching with ${providerDisplay.toUpperCase()}...`);
      if (options.grounding && providerDisplay === 'gemini') {
        console.error('🌐 Google Search grounding enabled');
      }
      console.error('');

      // Web調査を実行
      const result = await performWebResearch({
        query,
        model,
        provider,
        grounding: options.grounding,
      });

      // Markdownにフォーマット
      const markdown = formatResearchAsMarkdown(result);

      // ファイルに保存
      const filepath = await saveResearch(markdown, query);

      // 結果を出力
      console.log('✅ Research complete!');
      console.log('');
      console.log(`🤖 Model: ${result.metadata.model}`);
      console.log(`📊 Tokens used: ${result.metadata.tokens}`);
      console.log(`🔗 Sources found: ${result.sources.length}`);
      console.log(`📁 Saved to: ${filepath}`);
      console.log('');
      console.log('---');
      console.log('');
      console.log(markdown);

    } catch (error) {
      if (error instanceof Error) {
        console.error(`❌ Error: ${error.message}`);

        // APIキーエラーの場合は詳細なヘルプを表示
        if (error.message.includes('API key') || error.message.includes('401') || error.message.includes('not configured')) {
          console.error('');
          console.error('💡 Tip: Make sure API keys are set in your environment:');
          console.error('   For OpenAI: export OPENAI_API_KEY="sk-proj-..."');
          console.error('   For Gemini: export GEMINI_API_KEY="..."');
          console.error('   or add them to mcp-chatgpt-server/.env');
        }
      } else {
        console.error(`❌ Unknown error: ${String(error)}`);
      }
      process.exit(1);
    }
  });

// エラーハンドリング
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error.message);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection:', reason);
  process.exit(1);
});

program.parse();
