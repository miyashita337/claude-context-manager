/**
 * Token estimation utilities using tiktoken
 */

import { Tiktoken, get_encoding } from 'tiktoken';

let encoder: Tiktoken | null = null;

/**
 * Initialize tiktoken encoder (lazy loading)
 */
function getEncoder(): Tiktoken {
  if (!encoder) {
    // Use p50k_base as approximation for Claude 3
    encoder = get_encoding('p50k_base');
  }
  return encoder;
}

/**
 * Estimate token count for text using tiktoken
 * @param text Text to estimate tokens for
 * @returns Estimated token count
 */
export function estimateTokens(text: string): number {
  try {
    const enc = getEncoder();
    const tokens = enc.encode(text);
    return tokens.length;
  } catch (error) {
    // Fallback to simple heuristic if tiktoken fails
    return Math.ceil(text.length / 4);
  }
}

/**
 * Cleanup encoder resources
 */
export function cleanup(): void {
  if (encoder) {
    encoder.free();
    encoder = null;
  }
}
