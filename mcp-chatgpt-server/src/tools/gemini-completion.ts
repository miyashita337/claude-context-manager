import { GoogleGenerativeAI, GenerativeModel } from '@google/generative-ai';
import { z } from 'zod';
import { config } from '../config.js';
import type { ResearchResult, Finding, Source } from './types.js';

// Gemini クライアントの初期化
let genAI: GoogleGenerativeAI | null = null;
if (config.geminiApiKey) {
  genAI = new GoogleGenerativeAI(config.geminiApiKey);
}

// Gemini調査の引数スキーマ
export const GeminiResearchArgsSchema = z.object({
  query: z.string().describe('Research topic or question'),
  model: z.string().default(config.geminiModel).describe('Gemini model to use'),
  grounding: z.boolean().default(true).describe('Enable Google Search grounding'),
});

export type GeminiResearchArgs = z.infer<typeof GeminiResearchArgsSchema>;

// Gemini で Web調査を実行
export async function performGeminiResearch(args: GeminiResearchArgs): Promise<ResearchResult> {
  if (!genAI) {
    throw new Error('GEMINI_API_KEY is not configured');
  }

  try {
    const systemInstruction = `You are a research assistant. When providing information:
1. Always cite your sources with clickable URLs
2. Format citations as markdown links: [Source Title](URL)
3. Organize your response with clear headings for different findings
4. For each major finding, provide:
   - A clear claim or statement
   - Supporting evidence
   - Source URLs when available
5. Rate the reliability of each source (1-5 stars):
   - 5 stars: Official documentation, government sources, academic papers from .edu/.gov domains
   - 4 stars: Reputable news sources, established tech blogs, verified expert sources
   - 3 stars: General news sites, Wikipedia, Stack Overflow
   - 2 stars: Personal blogs, forums
   - 1 star: Unverified sources

Format your response clearly with headings and bullet points.`;

    const enhancedQuery = `Research the following topic comprehensively. Provide:
1. Key findings with supporting evidence
2. Multiple perspectives when relevant
3. Latest information available
4. Cite specific examples, studies, or sources
5. Format citations as [Source Name](URL) when you reference them

Topic: ${args.query}`;

    // モデル設定
    const modelConfig: any = {
      model: args.model,
      systemInstruction,
    };

    // Grounding（Google検索）を有効化
    if (args.grounding) {
      modelConfig.tools = [
        {
          googleSearch: {},
        },
      ];
    }

    const model: GenerativeModel = genAI.getGenerativeModel(modelConfig);

    // 生成設定
    const generationConfig = {
      temperature: config.geminiTemperature,
      maxOutputTokens: config.geminiMaxTokens,
    };

    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: enhancedQuery }] }],
      generationConfig,
    });

    const response = await result.response;
    const text = response.text();

    if (!text) {
      throw new Error('No response from Gemini');
    }

    // トークン使用量を取得
    const usageMetadata = response.usageMetadata;
    const totalTokens = usageMetadata
      ? (usageMetadata.promptTokenCount || 0) + (usageMetadata.candidatesTokenCount || 0)
      : 0;

    // レスポンスをパースして構造化
    const researchResult = parseGeminiResponse(text, args.query, args.model, totalTokens);

    return researchResult;
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Gemini API error: ${error.message}`);
    }
    throw error;
  }
}

// Geminiのレスポンスを構造化されたResearchResultに変換
function parseGeminiResponse(
  content: string,
  query: string,
  model: string,
  tokens: number
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
      model: `gemini:${model}`,
      tokens,
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
