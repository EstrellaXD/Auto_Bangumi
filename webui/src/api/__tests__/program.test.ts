/**
 * Contract tests for apiProgram: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/program.py fails a test instead of going
 * unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess, mockProgramStatus } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiProgram } from '@/api/program';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Program API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should POST api/v1/restart when restarting the program', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiProgram.restart();
    expect(axios.post).toHaveBeenCalledWith('api/v1/restart');
  });

  it('should POST api/v1/start when starting the program', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiProgram.start();
    expect(axios.post).toHaveBeenCalledWith('api/v1/start');
  });

  it('should POST api/v1/stop when stopping the program', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiProgram.stop();
    expect(axios.post).toHaveBeenCalledWith('api/v1/stop');
  });

  it('should GET api/v1/status when fetching program status', async () => {
    (axios.get as any).mockResolvedValue({ data: mockProgramStatus });
    await apiProgram.status();
    expect(axios.get).toHaveBeenCalledWith('api/v1/status');
  });

  it('should POST api/v1/shutdown when shutting down the program', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiProgram.shutdown();
    expect(axios.post).toHaveBeenCalledWith('api/v1/shutdown');
  });
});
