import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { ChatCompletionArgsSchema, callChatGPT } from './tools/chat-completion.js';
import { NanoBananaArgsSchema, generateDiagram } from './tools/nanobanana.js';

// MCPサーバーの作成
export function createServer() {
  const server = new Server(
    {
      name: 'mcp-chatgpt-server',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // ツール一覧の登録
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        {
          name: 'chatgpt',
          description: 'Send a message to ChatGPT and get a response. Use this when you need to consult ChatGPT for additional perspectives, specialized knowledge, or to compare responses.',
          inputSchema: {
            type: 'object',
            properties: {
              prompt: {
                type: 'string',
                description: 'The message to send to ChatGPT',
              },
              model: {
                type: 'string',
                description: 'OpenAI model to use (default: gpt-4o)',
                enum: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
              },
              temperature: {
                type: 'number',
                description: 'Temperature for response randomness (0-2, default: 0.7)',
                minimum: 0,
                maximum: 2,
              },
              max_tokens: {
                type: 'number',
                description: 'Maximum tokens in response (default: 2000)',
                minimum: 1,
              },
            },
            required: ['prompt'],
          },
        },
        {
          name: 'generate-diagram',
          description: 'Generate a conceptual diagram or documentation image using Nano Banana (Gemini image model). Saves to docs/images/. NOT for flowcharts/architecture (use Mermaid).',
          inputSchema: {
            type: 'object',
            properties: {
              prompt: {
                type: 'string',
                description: 'Description of the image to generate',
              },
              filename: {
                type: 'string',
                description: 'Output filename (auto-generated if omitted)',
              },
              output_dir: {
                type: 'string',
                description: 'Output directory (default: docs/images/)',
              },
              aspect_ratio: {
                type: 'string',
                description: 'Aspect ratio (default: 16:9)',
                enum: ['1:1', '16:9', '4:3', '3:4', '9:16'],
              },
              resolution: {
                type: 'string',
                description: 'Resolution (default: 2K)',
                enum: ['512px', '1K', '2K', '4K'],
              },
            },
            required: ['prompt'],
          },
        },
      ],
    };
  });

  // ツール呼び出しハンドラ
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    if (name === 'chatgpt') {
      // Zodでバリデーション
      const validatedArgs = ChatCompletionArgsSchema.parse(args);

      // ChatGPT呼び出し
      const response = await callChatGPT(validatedArgs);

      return {
        content: [
          {
            type: 'text',
            text: `ChatGPT Response (${response.model}):\n\n${response.content}${
              response.usage
                ? `\n\n[Tokens used: ${response.usage.total_tokens} (prompt: ${response.usage.prompt_tokens}, completion: ${response.usage.completion_tokens})]`
                : ''
            }`,
          },
        ],
      };
    }

    if (name === 'generate-diagram') {
      const validatedArgs = NanoBananaArgsSchema.parse(args);
      const result = await generateDiagram(validatedArgs);

      if (!result.imagePath) {
        return {
          content: [{ type: 'text', text: `No image generated.\n\n${result.description}` }],
        };
      }

      return {
        content: [
          {
            type: 'text',
            text: `Image saved: ${result.imagePath}\nModel: ${result.model}\nMIME: ${result.mimeType}\n\n${result.description}`,
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  });

  return server;
}

// サーバー起動
export async function startServer() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('MCP ChatGPT Server running on stdio');
}
