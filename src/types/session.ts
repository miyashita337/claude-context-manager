/**
 * Type definitions for Claude Context Manager session data
 */

export interface LogEntry {
  timestamp: string;
  type: 'user' | 'assistant';
  content: string;
  tokens_estimate: number;
  tool_name?: string;
  tool_input?: Record<string, any>;
}

export interface SessionMetadata {
  session_id: string;
  start_time: string;
  end_time: string;
  total_tokens: number;
  user_tokens: number;
  assistant_tokens: number;
  compact_detected: boolean;
  entry_count: number;
}

export interface SessionStats {
  total_tokens: number;
  user_tokens: number;
  assistant_tokens: number;
  entry_count: number;
  duration_minutes: number;
}
