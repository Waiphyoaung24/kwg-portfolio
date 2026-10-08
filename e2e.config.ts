import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';

export default {
  // Read-only checks use exact assertions and require no model provider.
  targets: [{
    engine: web(),
    app: {
      url: process.env.APP_URL ?? 'http://127.0.0.1:8899',
      command: process.env.APP_URL ? undefined : {
        executable: process.execPath,
        args: ['node_modules/astro/bin/astro.mjs', 'dev', '--host', '127.0.0.1', '--port', '8899'],
        env: { PUBLIC_TRADING_FIXTURE: '1' },
        log: '.e2e/logs/app.log',
      },
    },
  }],
} satisfies E2EConfig;
