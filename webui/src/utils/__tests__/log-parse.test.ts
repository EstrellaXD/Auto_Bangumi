import { describe, expect, it } from 'vitest';
import { countLogLevels, parseLogLines } from '../log-parse';

const SAMPLE = [
  '[2026-07-03 15:02:11] INFO:  Version 3.3.0-beta.2 started',
  '[2026-07-03 15:02:14] INFO:  Checking 12 RSS feeds',
  '[2026-07-03 15:02:18] WARNING:  Slow response from qBittorrent',
  '[2026-07-03 15:03:22] ERROR:  Failed to send notification',
  '[2026-07-03 15:04:00] DEBUG:  Next RSS check in 15 min',
].join('\n');

const UVICORN_STYLE =
  '[2026-07-03 15:03:01] INFO:     INFO::module.core.context:Program running.';

const CLEAN_STYLE =
  '[2026-07-03 18:00:00] INFO:     module.core.context: Program running.';

describe('parseLogLines', () => {
  it('should parse date, level, and message from each line', () => {
    const entries = parseLogLines(SAMPLE);
    expect(entries).toHaveLength(5);
    expect(entries[2]).toMatchObject({
      date: '[2026-07-03 15:02:18]',
      type: 'WARNING',
    });
    expect(entries[2].content).toContain('Slow response from qBittorrent');
  });

  it('should start from the Version line when present', () => {
    const withPreamble = `old noise line\n${SAMPLE}`;
    const entries = parseLogLines(withPreamble);
    expect(entries).toHaveLength(5);
    expect(entries[0].content).toContain('Version');
  });

  it('should keep only the newest maxLines entries', () => {
    const entries = parseLogLines(SAMPLE, 2);
    expect(entries).toHaveLength(2);
    expect(entries[1].type).toBe('DEBUG');
  });

  it('should return empty array for empty input', () => {
    expect(parseLogLines('')).toEqual([]);
  });

  it('should split the duplicated level-and-module prefix into a module field', () => {
    const [entry] = parseLogLines(UVICORN_STYLE);
    expect(entry).toMatchObject({
      type: 'INFO',
      module: 'module.core.context',
      content: 'Program running.',
    });
  });

  it('should leave module empty when a line has no module prefix', () => {
    const [entry] = parseLogLines(SAMPLE);
    expect(entry.module).toBe('');
    expect(entry.content).toContain('Version 3.3.0-beta.2 started');
  });

  it('should parse the clean "module.path: message" prefix', () => {
    const [entry] = parseLogLines(CLEAN_STYLE);
    expect(entry).toMatchObject({
      type: 'INFO',
      module: 'module.core.context',
      content: 'Program running.',
    });
  });

  it('should not mistake a single-word colon prefix for a module', () => {
    const line = '[2026-07-03 18:00:00] ERROR:    Error: something broke';
    const [entry] = parseLogLines(line);
    expect(entry.module).toBe('');
    expect(entry.content).toBe('Error: something broke');
  });
});

describe('countLogLevels', () => {
  it('should count entries per level', () => {
    const counts = countLogLevels(parseLogLines(SAMPLE));
    expect(counts).toEqual({ INFO: 2, WARNING: 1, ERROR: 1, DEBUG: 1 });
  });

  it('should return zero counts for no entries', () => {
    expect(countLogLevels([])).toEqual({
      INFO: 0,
      WARNING: 0,
      ERROR: 0,
      DEBUG: 0,
    });
  });
});
