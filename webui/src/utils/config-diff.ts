import type { Config } from '#/config';

/** 逐段比较配置，返回有未保存改动的段名（顺序与 Config 键序一致） */
export function dirtyConfigGroups(saved: Config, current: Config): Array<keyof Config> {
  const keys = Object.keys(saved) as Array<keyof Config>;
  return keys.filter(
    (key) => JSON.stringify(saved[key]) !== JSON.stringify(current[key])
  );
}
