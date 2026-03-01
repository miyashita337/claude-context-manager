import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { NanoBananaArgsSchema, resolveOutputDir, generateImageFilename } from '../tools/nanobanana.js';

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
    const result = resolveOutputDir();
    expect(result).toBe('/project/root/docs/images');
  });

  it('falls back to cwd when CLAUDE_PROJECT_DIR is not set', () => {
    delete process.env.CLAUDE_PROJECT_DIR;
    const result = resolveOutputDir();
    expect(result).toContain('docs/images');
  });
});

// --- generateImageFilename ---
describe('generateImageFilename', () => {
  it('uses custom filename as-is if it has .png extension', () => {
    expect(generateImageFilename('test prompt', 'my-image.png')).toBe('my-image.png');
  });

  it('appends .png to custom filename without extension', () => {
    expect(generateImageFilename('test prompt', 'my-image')).toBe('my-image.png');
  });

  it('auto-generates filename with timestamp and sanitized prompt', () => {
    const filename = generateImageFilename('Hello World! Test Image');
    expect(filename).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}_hello-world-test-image\.png$/);
  });

  it('truncates long prompts to 50 characters', () => {
    const longPrompt = 'a'.repeat(100);
    const filename = generateImageFilename(longPrompt);
    // timestamp_<max50chars>.png
    const parts = filename.split('_');
    const namePart = parts.slice(1).join('_').replace('.png', '');
    expect(namePart.length).toBeLessThanOrEqual(50);
  });

  it('handles non-alphanumeric characters', () => {
    const filename = generateImageFilename('日本語テスト & special chars!@#$');
    expect(filename).toMatch(/\.png$/);
    // Non-alphanumeric chars become hyphens
    expect(filename).not.toMatch(/[^a-z0-9\-_.T]/);
  });

  it('falls back to "diagram" for empty sanitized prompt', () => {
    const filename = generateImageFilename('!!!');
    expect(filename).toMatch(/diagram\.png$/);
  });
});

// --- Zod schema validation ---
describe('NanoBananaArgsSchema', () => {
  it('validates with only required prompt field', () => {
    const result = NanoBananaArgsSchema.parse({ prompt: 'test' });
    expect(result.prompt).toBe('test');
    expect(result.filename).toBeUndefined();
    expect(result.output_dir).toBeUndefined();
    expect(result.aspect_ratio).toBeUndefined();
    expect(result.resolution).toBeUndefined();
  });

  it('validates with all optional fields', () => {
    const result = NanoBananaArgsSchema.parse({
      prompt: 'test',
      filename: 'output.png',
      output_dir: '/tmp',
      aspect_ratio: '16:9',
      resolution: '2K',
    });
    expect(result.aspect_ratio).toBe('16:9');
    expect(result.resolution).toBe('2K');
  });

  it('rejects missing prompt', () => {
    expect(() => NanoBananaArgsSchema.parse({})).toThrow();
  });

  it('rejects invalid aspect_ratio', () => {
    expect(() =>
      NanoBananaArgsSchema.parse({ prompt: 'test', aspect_ratio: '2:1' })
    ).toThrow();
  });

  it('rejects invalid resolution', () => {
    expect(() =>
      NanoBananaArgsSchema.parse({ prompt: 'test', resolution: '8K' })
    ).toThrow();
  });
});

// --- generateDiagram (mocked API) ---
describe('generateDiagram', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws when GEMINI_API_KEY is not set', async () => {
    // Mock config with empty API key
    vi.doMock('../config.js', () => ({
      config: {
        geminiApiKey: '',
        nanoBananaModel: 'gemini-3.1-flash-image-preview',
      },
    }));

    const { generateDiagram } = await import('../tools/nanobanana.js');
    await expect(generateDiagram({ prompt: 'test' })).rejects.toThrow('GEMINI_API_KEY is not configured');
  });

  it('returns text-only result when no image in response', async () => {
    vi.doMock('../config.js', () => ({
      config: {
        geminiApiKey: 'test-key',
        nanoBananaModel: 'gemini-3.1-flash-image-preview',
      },
    }));

    vi.doMock('@google/genai', () => ({
      GoogleGenAI: class {
        models = {
          generateContent: vi.fn().mockResolvedValue({
            candidates: [{
              content: {
                parts: [{ text: 'Here is a description but no image was generated.' }],
              },
            }],
          }),
        };
      },
    }));

    const { generateDiagram } = await import('../tools/nanobanana.js');
    const result = await generateDiagram({ prompt: 'test' });
    expect(result.imagePath).toBe('');
    expect(result.mimeType).toBe('text/plain');
    expect(result.description).toContain('description but no image');
  });

  it('saves image and returns path when API returns image', async () => {
    const fakeImageBase64 = Buffer.from('fake-png-data').toString('base64');

    vi.doMock('../config.js', () => ({
      config: {
        geminiApiKey: 'test-key',
        nanoBananaModel: 'gemini-3.1-flash-image-preview',
      },
    }));

    vi.doMock('@google/genai', () => ({
      GoogleGenAI: class {
        models = {
          generateContent: vi.fn().mockResolvedValue({
            candidates: [{
              content: {
                parts: [
                  { text: 'Generated diagram description' },
                  { inlineData: { data: fakeImageBase64, mimeType: 'image/png' } },
                ],
              },
            }],
          }),
        };
      },
    }));

    // Mock fs to avoid actual file writes
    vi.doMock('fs/promises', () => ({
      default: {
        access: vi.fn().mockResolvedValue(undefined),
        mkdir: vi.fn().mockResolvedValue(undefined),
        writeFile: vi.fn().mockResolvedValue(undefined),
      },
      access: vi.fn().mockResolvedValue(undefined),
      mkdir: vi.fn().mockResolvedValue(undefined),
      writeFile: vi.fn().mockResolvedValue(undefined),
    }));

    const { generateDiagram } = await import('../tools/nanobanana.js');
    const result = await generateDiagram({ prompt: 'test diagram', output_dir: '/tmp/test' });

    expect(result.imagePath).toMatch(/^\/tmp\/test\/.+\.png$/);
    expect(result.description).toBe('Generated diagram description');
    expect(result.model).toBe('gemini-3.1-flash-image-preview');
    expect(result.mimeType).toBe('image/png');
  });

  it('throws on empty API response', async () => {
    vi.doMock('../config.js', () => ({
      config: {
        geminiApiKey: 'test-key',
        nanoBananaModel: 'gemini-3.1-flash-image-preview',
      },
    }));

    vi.doMock('@google/genai', () => ({
      GoogleGenAI: class {
        models = {
          generateContent: vi.fn().mockResolvedValue({
            candidates: [{ content: { parts: [] } }],
          }),
        };
      },
    }));

    const { generateDiagram } = await import('../tools/nanobanana.js');
    await expect(generateDiagram({ prompt: 'test' })).rejects.toThrow('No response');
  });
});
