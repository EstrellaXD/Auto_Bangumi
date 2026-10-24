export interface SectionTop {
  id: string;
  /** 分区上缘相对滚动容器上缘的距离（px） */
  top: number;
}

/** 滚动到底部的容差（px） */
const SCROLL_BOTTOM_EPSILON = 10;
/** 分区上缘越过该锚线即视为当前分区（px） */
export const SCROLL_ANCHOR_OFFSET = 80;

/**
 * 计算当前高亮分区：触底时取最后一个；否则取上缘已越过锚线的最后一个，
 * 都未越过则取第一个。列表为空返回 undefined。
 */
export function pickActiveSection(
  tops: SectionTop[],
  atBottom: boolean
): string | undefined {
  if (tops.length === 0) return undefined;
  if (atBottom) return tops[tops.length - 1].id;
  let current = tops[0].id;
  for (const { id, top } of tops) {
    if (top <= SCROLL_ANCHOR_OFFSET) current = id;
  }
  return current;
}

/**
 * 容器是否已滚动到底部。内容不足一屏、容器无法滚动时不算触底，
 * 否则最后一个分区会一直高亮。
 */
export function isAtBottom({
  scrollTop,
  scrollHeight,
  clientHeight,
}: Pick<HTMLElement, 'scrollTop' | 'scrollHeight' | 'clientHeight'>): boolean {
  return (
    scrollHeight - clientHeight > SCROLL_BOTTOM_EPSILON &&
    scrollHeight - scrollTop - clientHeight <= SCROLL_BOTTOM_EPSILON
  );
}
