export interface SectionTop {
  id: string;
  /** 分区上缘相对滚动容器上缘的距离（px） */
  top: number;
}

/** 滚动到底部的容差（px） */
export const SCROLL_BOTTOM_EPSILON = 10;
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
