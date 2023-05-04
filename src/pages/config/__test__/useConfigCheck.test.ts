import { checkHost, checkIp, checkPort } from '../useConfigCheck';

describe('check methods', () => {
  it('check ip', () => {
    expect(checkIp('127.0.0.1')).toBe(true);
    expect(checkIp('127.0.1')).toBe(false);
    expect(checkIp('')).toBe(false);
  });

  it('check port', () => {
    expect(checkPort(80)).toBe(true);
    expect(checkPort(-1)).toBe(false);
    expect(checkPort(70000)).toBe(false);
    expect(checkPort()).toBe(false);
  });

  it('check host', () => {
    expect(checkHost('127.0.0.1:2523')).toContainEqual(true);
    expect(checkHost('127.0.0.1')).toContainEqual(false);
    expect(checkHost('127.0.1:')).toContainEqual(false);
    expect(checkHost(':2523')).toContainEqual(false);
    expect(checkHost('127.0.0.1:70000')).toContainEqual(false);
    expect(checkHost('dfajlskdfa0')).toContainEqual(false);
    expect(checkHost('')).toContainEqual(false);
  });
});
