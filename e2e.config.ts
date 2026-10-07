import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';

export default {
  // Read-only checks use exact assertions and require no model provider.
  targets: [{
    engine: web(),
    app: {
      url: process.env.APP_URL ?? 'http://127.0.0.1:8899',
      // Or let the runner start the dev server:
      // command: { executable: 'npm', args: ['run', 'dev'] },
    },
  }],
} satisfies E2EConfig;
