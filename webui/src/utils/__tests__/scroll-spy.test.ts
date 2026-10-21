import { describe, expect, it } from 'vitest';
import { isAtBottom, pickActiveSection } from '../scroll-spy';

const tops = [
  { id: 'a', top: -300 },
  { id: 'b', top: 40 },
  { id: 'c', top: 500 },
];

describe('pickActiveSection', () => {
  it('should return the last section crossing the anchor when not at bottom', () => {
    expect(pickActiveSection(tops, false)).toBe('b');
  });

  it('should return the first section when none crossed the anchor', () => {
    expect(pickActiveSection([{ id: 'a', top: 200 }], false)).toBe('a');
  });

  it('should return the last section when scrolled to the bottom', () => {
    expect(pickActiveSection(tops, true)).toBe('c');
  });

  it('should return undefined when there are no sections', () => {
    expect(pickActiveSection([], true)).toBeUndefined();
  });
});

describe('isAtBottom', () => {
  it.each([
    {
      when: 'the container cannot scroll',
      el: { scrollTop: 0, scrollHeight: 500, clientHeight: 500 },
      expected: false,
    },
    {
      when: 'a scrollable container is at the bottom',
      el: { scrollTop: 495, scrollHeight: 1000, clientHeight: 500 },
      expected: true,
    },
    {
      when: 'a scrollable container is above the bottom',
      el: { scrollTop: 100, scrollHeight: 1000, clientHeight: 500 },
      expected: false,
    },
  ])('should return $expected when $when', ({ el, expected }) => {
    expect(isAtBottom(el)).toBe(expected);
  });
});
