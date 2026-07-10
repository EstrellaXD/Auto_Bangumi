import { bootstrapAuthenticatedState } from '../fixtures/auth';
import { authStatePath } from '../fixtures/env';
import { test } from '../fixtures/test';

test('complete first-run setup for Firefox', async ({ page, environment }) => {
  await bootstrapAuthenticatedState(
    page,
    environment,
    authStatePath('firefox')
  );
});
