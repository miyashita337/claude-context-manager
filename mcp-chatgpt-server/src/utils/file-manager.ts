import * as fs from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// 調査結果を保存
export async function saveResearch(
  content: string,
  topic: string
): Promise<string> {
  const outputDir = path.join(process.env.HOME || '/Users/harieshokunin', '.claude', 'research');
  const filename = generateFilename(topic);
  const filepath = path.join(outputDir, filename);

  await ensureDirectoryExists(outputDir);
  await fs.writeFile(filepath, content, 'utf-8');

  return filepath;
}

// ファイル名を生成（YYYY-MM-DD_topic-name.md）
function generateFilename(topic: string): string {
  const date = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const sanitized = topic
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-') // 英数字以外をハイフンに
    .replace(/^-+|-+$/g, '') // 先頭と末尾のハイフンを削除
    .slice(0, 50); // 最大50文字

  return `${date}_${sanitized || 'research'}.md`;
}

// ディレクトリが存在しない場合は作成
async function ensureDirectoryExists(dir: string): Promise<void> {
  try {
    await fs.access(dir);
  } catch {
    await fs.mkdir(dir, { recursive: true });
  }
}
