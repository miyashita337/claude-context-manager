import OpenAI from 'openai';
import { z } from 'zod';
import { config, type ModelProvider } from '../config.js';
import type { ResearchResult, Finding, Source } from './types.js';
import { performGeminiResearch } from './gemini-completion.js';

// OpenAIクライアントの初期化
let openai: OpenAI | null = null;
if (config.openaiApiKey) {
  openai = new OpenAI({
    apiKey: config.openaiApiKey,
  });
}

// Web調査の引数スキーマ（拡張版）
export const WebResearchArgsSchema = z.object({
  query: z.string().describe('Research topic or question'),
  model: z.string().default('gpt-4o').describe('Model name to use'),
  provider: z.enum(['openai', 'gemini']).optional().describe('Model provider (openai or gemini)'),
  grounding: z.boolean().default(false).describe('Enable Google Search grounding (Gemini only)'),
});

export type WebResearchArgs = z.infer<typeof WebResearchArgsSchema>;

// Web調査を実行（プロバイダー選択）
export async function performWebResearch(args: WebResearchArgs): Promise<ResearchResult> {
  // プロバイダーを決定
  let provider: ModelProvider = args.provider || config.defaultProvider;

  // モデル名から自動判定
  if (!args.provider) {
    if (args.model.startsWith('gemini')) {
      provider = 'gemini';
    } else if (args.model.startsWith('gpt')) {
      provider = 'openai';
    }
  }

  // プロバイダーに応じて処理を分岐
  if (provider === 'gemini') {
    return performGeminiResearch({
      query: args.query,
      model: args.model.startsWith('gemini') ? args.model : config.geminiModel,
      grounding: args.grounding,
    });
  } else {
    return performOpenAIResearch({
      query: args.query,
      model: args.model.startsWith('gpt') ? args.model : config.openaiModel,
    });
  }
}

// OpenAI で Web調査を実行
async function performOpenAIResearch(args: { query: string; model: string }): Promise<ResearchResult> {
  if (!openai) {
    throw new Error('OPENAI_API_KEY is not configured');
  }
  try {
    const systemPrompt = `You are a research assistant. When providing information:
1. Always cite your sources with clickable URLs
2. Format citations as markdown links: [Source Title](URL)
3. Organize your response with clear headings for different findings
4. For each major finding, provide:
   - A clear claim or statement
   - Supporting evidence
   - Source URLs
5. Rate the reliability of each source (1-5 stars):
   - 5 stars: Official documentation, government sources, academic papers from .edu/.gov domains
   - 4 stars: Reputable news sources, established tech blogs, verified expert sources
   - 3 stars: General news sites, Wikipedia, Stack Overflow
   - 2 stars: Personal blogs, forums
   - 1 star: Unverified sources

Format your response clearly with headings and bullet points.`;

    // Note: OpenAI APIは現在Web検索toolsを直接サポートしていません
    // プロンプトエンジニアリングで調査品質を向上させます
    const enhancedQuery = `Research the following topic comprehensively. Provide:
1. Key findings with supporting evidence
2. Multiple perspectives when relevant
3. Latest information you're aware of (up to your knowledge cutoff)
4. Cite specific examples, studies, or sources when possible
5. Format citations as [Source Name](URL) when you reference them

Topic: ${args.query}`;

    const completion = await openai.chat.completions.create({
      model: args.model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: enhancedQuery }
      ],
      temperature: 0.7,
    });

    const message = completion.choices[0]?.message;

    if (!message?.content) {
      throw new Error('No response from ChatGPT');
    }

    // レスポンスをパースして構造化
    const result = parseResearchResponse(message.content, args.query, completion);

    return result;
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Web research error: ${error.message}`);
    }
    throw error;
  }
}

// OpenAIのレスポンスを構造化されたResearchResultに変換
function parseResearchResponse(
  content: string,
  query: string,
  completion: OpenAI.Chat.Completions.ChatCompletion
): ResearchResult {
  // URLを抽出（マークダウンリンクとプレーンURL両方）
  const urlPattern = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)|https?:\/\/[^\s\)]+/g;
  const urlMatches = [...content.matchAll(urlPattern)];

  const extractedSources: Source[] = [];
  const seenUrls = new Set<string>();

  for (const match of urlMatches) {
    let url: string;
    let title: string;

    if (match[2]) {
      // マークダウンリンク: [Title](URL)
      title = match[1];
      url = match[2];
    } else {
      // プレーンURL
      url = match[0];
      title = new URL(url).hostname;
    }

    if (!seenUrls.has(url)) {
      seenUrls.add(url);
      extractedSources.push({
        url,
        title,
        accessDate: new Date().toISOString().split('T')[0], // YYYY-MM-DD
      });
    }
  }

  // コンテンツをセクションに分割（## または ### で始まる行）
  const sections = content.split(/^##+ /m).filter(s => s.trim().length > 0);

  const findings: Finding[] = sections.map((section, index) => {
    const lines = section.split('\n');
    const title = lines[0]?.trim() || `Finding ${index + 1}`;
    const body = lines.slice(1).join('\n').trim();

    // このセクション内のURLを抽出
    const sectionUrls = [...body.matchAll(urlPattern)].map(m => m[2] || m[0]);

    // 信頼性スコアを推定（ドメインベース）
    const reliability = estimateReliability(sectionUrls);

    return {
      title,
      claim: extractFirstSentence(body) || title,
      evidence: body.slice(0, 500), // 最初の500文字を証拠として
      sources: sectionUrls,
      reliability,
    };
  });

  // ファインディングがない場合は、全体を1つのファインディングとして扱う
  if (findings.length === 0) {
    const allUrls = extractedSources.map(s => s.url);
    findings.push({
      title: query,
      claim: extractFirstSentence(content) || query,
      evidence: content.slice(0, 500),
      sources: allUrls,
      reliability: estimateReliability(allUrls),
    });
  }

  return {
    query,
    findings,
    sources: extractedSources,
    metadata: {
      timestamp: new Date().toISOString(),
      model: completion.model,
      tokens: completion.usage?.total_tokens || 0,
    },
  };
}

// 最初の文を抽出
function extractFirstSentence(text: string): string {
  const match = text.match(/^[^.!?]+[.!?]/);
  return match ? match[0].trim() : text.slice(0, 200);
}

// URLのドメインに基づいて信頼性スコアを推定
function estimateReliability(urls: string[]): number {
  if (urls.length === 0) return 3; // デフォルト

  const scores = urls.map(url => {
    try {
      const hostname = new URL(url).hostname.toLowerCase();

      // 公式ドキュメント、政府、学術機関
      if (hostname.endsWith('.gov') || hostname.endsWith('.edu') ||
          hostname.includes('github.com') || hostname.includes('docs.')) {
        return 5;
      }

      // 信頼できるニュース/技術サイト
      if (hostname.includes('stackoverflow.com') || hostname.includes('medium.com') ||
          hostname.includes('techcrunch.com') || hostname.includes('arxiv.org')) {
        return 4;
      }

      // 一般的なニュース、Wikipedia
      if (hostname.includes('wikipedia.org') || hostname.includes('news')) {
        return 3;
      }

      // その他
      return 2;
    } catch {
      return 2;
    }
  });

  // 平均スコア
  const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
  return Math.round(avgScore);
}
