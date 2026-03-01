import { GoogleGenAI } from '@google/genai';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';
import { config } from '../config.js';

// Zod スキーマ
export const NanoBananaArgsSchema = z.object({
  prompt: z.string().describe('Description of the image to generate'),
  filename: z.string().optional().describe('Output filename (auto-generated if omitted)'),
  output_dir: z.string().optional().describe('Output directory (default: docs/images/)'),
  aspect_ratio: z.enum(['1:1', '16:9', '4:3', '3:4', '9:16']).optional().describe('Aspect ratio (default: 16:9)'),
  resolution: z.enum(['512px', '1K', '2K', '4K']).optional().describe('Resolution (default: 2K)'),
});

export type NanoBananaArgs = z.infer<typeof NanoBananaArgsSchema>;

export interface GenerateDiagramResult {
  imagePath: string;
  description: string;
  model: string;
  mimeType: string;
}

// 出力ディレクトリ解決
export function resolveOutputDir(overrideDir?: string): string {
  if (overrideDir) return overrideDir;
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  return path.join(projectDir, 'docs', 'images');
}

// ファイル名生成（タイムスタンプ + サニタイズされたプロンプト）
export function generateImageFilename(prompt: string, customFilename?: string): string {
  if (customFilename) {
    return customFilename.endsWith('.png') ? customFilename : `${customFilename}.png`;
  }

  const date = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const sanitized = prompt
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50);

  return `${date}_${sanitized || 'diagram'}.png`;
}

// ディレクトリが存在しない場合は作成
async function ensureDirectoryExists(dir: string): Promise<void> {
  try {
    await fs.access(dir);
  } catch {
    await fs.mkdir(dir, { recursive: true });
  }
}

// 画像生成メイン関数
export async function generateDiagram(args: NanoBananaArgs): Promise<GenerateDiagramResult> {
  if (!config.geminiApiKey) {
    throw new Error(
      'GEMINI_API_KEY is not configured. Set it in mcp-chatgpt-server/.env or as an environment variable.'
    );
  }

  const ai = new GoogleGenAI({ apiKey: config.geminiApiKey });
  const model = config.nanoBananaModel;

  const response = await ai.models.generateContent({
    model,
    contents: args.prompt,
    config: {
      responseModalities: ['TEXT', 'IMAGE'],
      imageConfig: {
        aspectRatio: args.aspect_ratio || '16:9',
        imageSize: args.resolution || '2K',
      },
    },
  });

  // レスポンスからテキストと画像を抽出
  const parts = response.candidates?.[0]?.content?.parts;
  if (!parts || parts.length === 0) {
    throw new Error('No response from Nano Banana model');
  }

  let description = '';
  let imageData: string | null = null;
  let mimeType = 'image/png';

  for (const part of parts) {
    if (part.text) {
      description += part.text;
    }
    if (part.inlineData) {
      imageData = part.inlineData.data as string;
      mimeType = part.inlineData.mimeType || 'image/png';
    }
  }

  if (!imageData) {
    return {
      imagePath: '',
      description: description || 'The model returned text only without generating an image.',
      model,
      mimeType: 'text/plain',
    };
  }

  // ファイル保存
  const outputDir = resolveOutputDir(args.output_dir);
  await ensureDirectoryExists(outputDir);

  const filename = generateImageFilename(args.prompt, args.filename);
  const imagePath = path.join(outputDir, filename);

  const buffer = Buffer.from(imageData, 'base64');
  await fs.writeFile(imagePath, buffer);

  return {
    imagePath,
    description: description || 'Image generated successfully.',
    model,
    mimeType,
  };
}
