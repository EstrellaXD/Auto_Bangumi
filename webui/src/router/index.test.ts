import { router } from './index';

// setup.ts 全局 mock 了 vue-router，这里换回真实模块
vi.unmock('vue-router');

describe('router', () => {
  it('should register file-based routes when the module loads', () => {
    expect(router.getRoutes().length).toBeGreaterThan(0);
  });
});
