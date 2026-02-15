import OpenAI from 'openai';
import { z } from 'zod';
import { config } from '../config.js';
import type { ChatCompletionResponse } from './types.js';

// OpenAIクライアントの初期化
const openai = new OpenAI({
  apiKey: config.openaiApiKey,
});

// ツールの引数スキーマ（Zod）
export const ChatCompletionArgsSchema = z.object({
  prompt: z.string().describe('The message to send to ChatGPT'),
  model: z.string().optional().default(config.defaultModel).describe('OpenAI model to use'),
  temperature: z.number().min(0).max(2).optional().default(config.defaultTemperature),
  max_tokens: z.number().positive().optional().default(config.defaultMaxTokens),
});

export type ChatCompletionArgs = z.infer<typeof ChatCompletionArgsSchema>;

// ChatGPT呼び出し関数
export async function callChatGPT(args: ChatCompletionArgs): Promise<ChatCompletionResponse> {
  try {
    const completion = await openai.chat.completions.create({
      model: args.model,
      messages: [
        {
          role: 'user',
          content: args.prompt,
        },
      ],
      temperature: args.temperature,
      max_tokens: args.max_tokens,
    });

    const message = completion.choices[0]?.message;

    if (!message?.content) {
      throw new Error('No response from ChatGPT');
    }

    return {
      content: message.content,
      model: completion.model,
      usage: completion.usage ? {
        prompt_tokens: completion.usage.prompt_tokens,
        completion_tokens: completion.usage.completion_tokens,
        total_tokens: completion.usage.total_tokens,
      } : undefined,
    };
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`ChatGPT API error: ${error.message}`);
    }
    throw error;
  }
}
