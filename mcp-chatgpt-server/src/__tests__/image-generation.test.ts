import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  GenerateImageArgsSchema,
  resolveOutputDir,
  generateImageFilename,
} from '../tools/image-generation.js';

// --- resolveOutputDir ---
describe('resolveOutputDir', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('returns override dir when provided', () => {
    expect(resolveOutputDir('/custom/path')).toBe('/custom/path');
  });

  it('uses CLAUDE_PROJECT_DIR when set', () => {
    process.env.CLAUDE_PROJECT_DIR = '/project/root';
    expect(resolveOutputDir()).toBe('/project/root/docs/images');
  });

  it('falls back to cwd when CLAUDE_PROJECT_DIR is unset', () => {
    delete process.env.CLAUDE_PROJECT_DIR;
    expect(resolveOutputDir()).toBe(`${process.cwd()}/docs/images`);
  });
});

// --- generateImageFilename ---
describe('generateImageFilename', () => {
  it('uses custom filename as-is if it already has the extension', () => {
    expect(generateImageFilename('test prompt', 'my-image.png')).toBe('my-image.png');
  });

  it('appends the extension to a custom filename without one', () => {
    expect(generateImageFilename('test prompt', 'my-image')).toBe('my-image.png');
  });

  it('honors a non-png output format for the extension', () => {
    expect(generateImageFilename('test prompt', 'my-image', 'webp')).toBe('my-image.webp');
    expect(generateImageFilename('test prompt', undefined, 'jpeg')).toMatch(/\.jpeg$/);
  });

  it('does not double-append when the custom name already has that extension', () => {
    expect(generateImageFilename('p', 'shot.webp', 'webp')).toBe('shot.webp');
  });

  it('auto-generates filename with timestamp and sanitized prompt', () => {
    const filename = generateImageFilename('Hello World! Test Image');
    expect(filename).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}_hello-world-test-image\.png$/);
  });

  it('truncates long prompts to 50 characters', () => {
    const filename = generateImageFilename('a'.repeat(100));
    const parts = filename.split('_');
    const namePart = parts.slice(1).join('_').replace('.png', '');
    expect(namePart.length).toBeLessThanOrEqual(50);
  });

  it('handles non-alphanumeric characters', () => {
    const filename = generateImageFilename('日本語テスト & special chars!@#$');
    expect(filename).toMatch(/\.png$/);
    expect(filename).not.toMatch(/[^a-z0-9\-_.T]/);
  });

  it('falls back to "diagram" for empty sanitized prompt', () => {
    expect(generateImageFilename('!!!')).toMatch(/diagram\.png$/);
  });
});

// --- Zod schema validation ---
// 許容値の出典: openai@4.104.0 node_modules/openai/resources/images.d.ts:242-287
describe('GenerateImageArgsSchema', () => {
  it('validates with only the required prompt field', () => {
    const result = GenerateImageArgsSchema.parse({ prompt: 'test' });
    expect(result.prompt).toBe('test');
    expect(result.filename).toBeUndefined();
    expect(result.output_dir).toBeUndefined();
    expect(result.size).toBeUndefined();
    expect(result.quality).toBeUndefined();
    expect(result.output_format).toBeUndefined();
  });

  it('accepts every size supported by gpt-image-1', () => {
    for (const size of ['auto', '1024x1024', '1536x1024', '1024x1536'] as const) {
      expect(GenerateImageArgsSchema.parse({ prompt: 'p', size }).size).toBe(size);
    }
  });

  it('accepts every quality level', () => {
    for (const quality of ['auto', 'low', 'medium', 'high'] as const) {
      expect(GenerateImageArgsSchema.parse({ prompt: 'p', quality }).quality).toBe(quality);
    }
  });

  it('accepts every output format', () => {
    for (const fmt of ['png', 'jpeg', 'webp'] as const) {
      expect(GenerateImageArgsSchema.parse({ prompt: 'p', output_format: fmt }).output_format).toBe(fmt);
    }
  });

  it('rejects the retired Gemini-era aspect ratio values', () => {
    // gpt-image-1 に 16:9 / 4K 相当は存在しない。黙って近似せず弾く。
    expect(() => GenerateImageArgsSchema.parse({ prompt: 'p', size: '16:9' })).toThrow();
    expect(() => GenerateImageArgsSchema.parse({ prompt: 'p', quality: '4K' })).toThrow();
  });

  it('rejects a missing prompt', () => {
    expect(() => GenerateImageArgsSchema.parse({})).toThrow();
  });
});
