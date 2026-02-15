// OpenAI APIのリクエスト/レスポンス型定義
export interface ChatCompletionRequest {
  prompt: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface ChatCompletionResponse {
  content: string;
  model: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// Web調査関連の型定義
export interface ResearchResult {
  query: string;
  findings: Finding[];
  sources: Source[];
  metadata: {
    timestamp: string;
    model: string;
    tokens: number;
  };
}

export interface Finding {
  title: string;
  claim: string;
  evidence: string;
  sources: string[]; // URLs
  reliability: number; // 1-5 stars
}

export interface Source {
  url: string;
  title: string;
  accessDate: string;
}
