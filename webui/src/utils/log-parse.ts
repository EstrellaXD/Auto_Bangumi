export type LogLevel = 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';

export interface LogEntry {
  index: number;
  date: string;
  type: string;
  /** 来源模块（如 module.core.context），无法解析时为空串 */
  module: string;
  content: string;
}

// 模块前缀两种格式，拆成模块字段：
// 旧日志文件："LEVEL::module.path:message"（QueueHandler 默认格式化的遗留行）
// 新格式："module.path: message"（要求带点号，避免把 "Error:" 之类误判为模块）
const LEGACY_MODULE_PREFIX = /^(?:INFO|WARNING|ERROR|DEBUG)::([\w.]+):/;
const MODULE_PREFIX = /^([A-Za-z_]\w*(?:\.\w+)+): /;

export type LogLevelCounts = Record<LogLevel, number>;

/** 解析原始日志文本：从最近一次 Version 行开始，仅保留最新 maxLines 行 */
export function parseLogLines(raw: string, maxLines = 1000): LogEntry[] {
  const list = raw
    .trim()
    .split('\n')
    .filter((i) => i !== '');
  const startIndex = list.findIndex((i) => /Version/.test(i));

  return list
    .slice(startIndex === -1 ? 0 : startIndex)
    .slice(-maxLines)
    .map((i, index) => {
      const date = i.match(/\[\d+-\d+-\d+\ \d+:\d+:\d+\]/)?.[0] || '';
      const type = i.match(/(INFO)|(WARNING)|(ERROR)|(DEBUG)/)?.[0] || '';
      let content = i.replace(date, '').replace(`${type}:`, '').trim();

      const moduleMatch =
        content.match(LEGACY_MODULE_PREFIX) ?? content.match(MODULE_PREFIX);
      const module = moduleMatch?.[1] ?? '';
      if (moduleMatch) {
        content = content.slice(moduleMatch[0].length).trim();
      }

      return { index, date, type, module, content };
    })
    .filter((entry) => entry.content !== '');
}

export function countLogLevels(entries: LogEntry[]): LogLevelCounts {
  const counts: LogLevelCounts = { INFO: 0, WARNING: 0, ERROR: 0, DEBUG: 0 };
  for (const entry of entries) {
    if (entry.type in counts) counts[entry.type as LogLevel] += 1;
  }
  return counts;
}
