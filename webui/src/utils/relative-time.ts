/** 相对时间（刚刚 / N 分钟前 / N 小时前 / N 天前），一周以上显示日期 */
export function relativeTime(
  t: (key: string, params?: Record<string, unknown>) => string,
  time: string | number,
  now = Date.now()
): string {
  const then = new Date(time).getTime();
  if (Number.isNaN(then)) return '';
  const minutes = Math.floor((now - then) / 60000);
  if (minutes < 1) return t('notifications.time.just_now');
  if (minutes < 60) return t('notifications.time.minutes_ago', { n: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t('notifications.time.hours_ago', { n: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return t('notifications.time.days_ago', { n: days });
  return new Date(time).toLocaleDateString();
}
