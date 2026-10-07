import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('saved learning result survives navigation without submitting a prompt', async ({ app, screen }) => {
  await app.open('/?session=0edab1e6d735');
  const answer = screen.getByText('{"row_count":6,"sum":130,"positive_count":3,"mean":21.67}');
  await expect(answer).toBeVisible();
  await expect(screen.getByRole('button', 'Send message')).toBeDisabled();
  const trace = screen.getByRole('button', 'Done · 4 steps · 41s');
  if (await trace.getAttribute('aria-expanded') === 'false') await trace.tap();
  await expect(trace).toBeExpanded();
  await expect(screen.getByText('Verify financial analysis')).toBeVisible();
  await screen.getByRole('link', 'Reports').tap();
  await expect(screen.getByRole('heading', 'Backtest Report Library')).toBeVisible();
  await expect(screen.getByRole('heading', 'No reports yet')).toBeVisible();
  await app.back();
  await expect(answer).toBeVisible();
  await app.screenshot('saved-synthetic-result');
});

test('runtime displays no authorized brokers or running runners', async ({ app, screen }) => {
  await app.open('/runtime');
  await expect(screen.getByRole('heading', 'Live / Paper Runtime Status')).toBeVisible();
  await expect(screen.getByRole('main')).toContainText(/\bAUTHORIZED\s+0\b/);
  await expect(screen.getByText('0 running')).toBeVisible();
});
