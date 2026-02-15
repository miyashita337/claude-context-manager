import { startServer } from './server.js';

// エラーハンドリング
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// サーバー起動
startServer().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
