import type { ResearchResult } from '../tools/types.js';

// ResearchResultを構造化Markdownに変換
export function formatResearchAsMarkdown(result: ResearchResult): string {
  const stars = (count: number) => '⭐'.repeat(count);

  const findingsSection = result.findings.map((finding, index) => `
###  ${index + 1}. ${finding.title}

- **主張**: ${finding.claim}
- **根拠**: ${finding.evidence}
- **出典**: ${finding.sources.length > 0 ? finding.sources.map(url => `[Link](${url})`).join(', ') : 'なし'}
- **信頼性**: ${stars(finding.reliability)} (${finding.reliability}/5)
`).join('\n');

  const sourcesSection = result.sources.length > 0
    ? result.sources.map((source, index) =>
        `${index + 1}. [${source.title}](${source.url}) - アクセス日: ${source.accessDate}`
      ).join('\n')
    : '出典情報なし';

  return `# 調査結果: ${result.query}

## メタ情報

- **調査日時**: ${new Date(result.metadata.timestamp).toLocaleString('ja-JP')}
- **調査ツール**: ChatGPT (${result.metadata.model}) + Web Search
- **トークン使用**: ${result.metadata.tokens} tokens

## 主要な発見
${findingsSection}

## 参考文献

${sourcesSection}

---

*このレポートは[ChatGPT](https://openai.com) Web Search APIにより自動生成されました。*
`;
}
