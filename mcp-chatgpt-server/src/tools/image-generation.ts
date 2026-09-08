import OpenAI from 'openai';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';
import { config } from '../config.js';

// 引数の許容値はインストール済み SDK の型定義を出典とする:
//   openai@4.104.0 node_modules/openai/resources/images.d.ts
//     :62      ImageModel = 'dall-e-2' | 'dall-e-3' | 'gpt-image-1'
//     :242-287 ImageGenerateParams (model / n / output_format / quality / size)
// gpt-image-1 が受け付ける size は下記 4 種のみ。Gemini 時代の aspect_ratio(5種) /
// resolution(4段階) に相当する値は存在しないため、OpenAI ネイティブの引数へ置き換えた。
export const GenerateImageArgsSchema = z.object({
  prompt: z.string().describe('Description of the image to generate'),
  filename: z.string().optional().describe('Output filename (auto-generated if omitted)'),
  output_dir: z.string().optional().describe('Output directory (default: docs/images/)'),
  size: z
    .enum(['auto', '1024x1024', '1536x1024', '1024x1536'])
    .optional()
    .describe('Image size (default: 1536x1024 landscape)'),
  quality: z
    .enum(['auto', 'low', 'medium', 'high'])
    .optional()
    .describe('Rendering quality (default: medium)'),
  output_format: z.enum(['png', 'jpeg', 'webp']).optional().describe('File format (default: png)'),
});

export type GenerateImageArgs = z.infer<typeof GenerateImageArgsSchema>;

export interface GenerateImageResult {
  imagePath: string;
  description: string;
  model: string;
  mimeType: string;
}

const MIME_BY_FORMAT: Record<string, string> = {
  png: 'image/png',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
};

// 出力ディレクトリ解決
export function resolveOutputDir(overrideDir?: string): string {
  if (overrideDir) return overrideDir;
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  return path.join(projectDir, 'docs', 'images');
}

// ファイル名生成（タイムスタンプ + サニタイズされたプロンプト）
export function generateImageFilename(
  prompt: string,
  customFilename?: string,
  format: string = 'png'
): string {
  const ext = `.${format}`;

  if (customFilename) {
    return customFilename.endsWith(ext) ? customFilename : `${customFilename}${ext}`;
  }

  const date = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const sanitized = prompt
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50);

  return `${date}_${sanitized || 'diagram'}${ext}`;
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
export async function generateImage(args: GenerateImageArgs): Promise<GenerateImageResult> {
  if (!config.openaiApiKey) {
    throw new Error(
      'OPENAI_API_KEY is not configured. Set it in mcp-chatgpt-server/.env or as an environment variable.'
    );
  }

  const openai = new OpenAI({ apiKey: config.openaiApiKey });
  const model = config.imageModel;
  const format = args.output_format || config.imageFormat;

  // response_format は送らない: gpt-image-1 は常に base64 を返し、dall-e 系は既定で URL を返す。
  // どちらの応答形でも下で受けられるようにしておく（モデルごとの分岐を持たないため）。
  const response = await openai.images.generate({
    model,
    prompt: args.prompt,
    size: args.size || config.imageSize,
    quality: args.quality || config.imageQuality,
    output_format: format,
    n: 1,
  });

  const image = response.data?.[0];
  if (!image) {
    throw new Error(`No image returned by model ${model}`);
  }

  let buffer: Buffer;
  if (image.b64_json) {
    buffer = Buffer.from(image.b64_json, 'base64');
  } else if (image.url) {
    const res = await fetch(image.url);
    if (!res.ok) {
      throw new Error(`Failed to download generated image: ${res.status} ${res.statusText}`);
    }
    buffer = Buffer.from(await res.arrayBuffer());
  } else {
    throw new Error(`Model ${model} returned neither b64_json nor url`);
  }

  // ファイル保存
  const outputDir = resolveOutputDir(args.output_dir);
  await ensureDirectoryExists(outputDir);

  const filename = generateImageFilename(args.prompt, args.filename, format);
  const imagePath = path.join(outputDir, filename);
  await fs.writeFile(imagePath, buffer);

  return {
    imagePath,
    // revised_prompt は dall-e-3 のみ返す（images.d.ts:52 "For `dall-e-3` only"）。
    // gpt-image-1 では未設定になるため既定文言にフォールバックする。
    description: image.revised_prompt || 'Image generated successfully.',
    model,
    mimeType: MIME_BY_FORMAT[format] || 'image/png',
  };
}
