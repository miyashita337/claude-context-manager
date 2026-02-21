import * as dotenv from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 1. mcp-chatgpt-server/.env を優先ロード
dotenv.config({ path: resolve(__dirname, '../.env') });
// 2. プロジェクトルートの .env をフォールバックとしてロード（上書きしない）
dotenv.config({ path: resolve(__dirname, '../../.env') });

export type ModelProvider = 'openai' | 'gemini';

export const config = {
  // Provider selection
  defaultProvider: (process.env.DEFAULT_MODEL || 'openai') as ModelProvider,

  // OpenAI settings
  openaiApiKey: process.env.OPENAI_API_KEY || '',
  openaiModel: process.env.OPENAI_MODEL || 'gpt-4o',
  openaiTemperature: parseFloat(process.env.OPENAI_TEMPERATURE || '0.7'),
  openaiMaxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '2000', 10),

  // Gemini settings
  geminiApiKey: process.env.GEMINI_API_KEY || '',
  geminiModel: process.env.GEMINI_MODEL || 'gemini-2.5-flash',
  geminiTemperature: parseFloat(process.env.GEMINI_TEMPERATURE || '0.7'),
  geminiMaxTokens: parseInt(process.env.GEMINI_MAX_TOKENS || '2000', 10),

  // Legacy aliases for backward compatibility
  get defaultModel() { return this.openaiModel; },
  get defaultTemperature() { return this.openaiTemperature; },
  get defaultMaxTokens() { return this.openaiMaxTokens; },
};

// APIキーの検証（少なくとも1つは必要）
if (!config.openaiApiKey && !config.geminiApiKey) {
  throw new Error('At least one API key (OPENAI_API_KEY or GEMINI_API_KEY) is required');
}
